import streamlit as st
import pandas as pd
import yaml
import logging
import io
import contextlib
import traceback
from typing import List, Tuple, Dict, Any, Optional, Callable
from google import genai
from google.genai import types
from config import MONTH_COLUMNS
import ast
import io
import contextlib
# ============================================================
# Constants & Configuration
# ============================================================
MODEL_PRIMARY = "gemini-3-flash-preview"
MODEL_FALLBACKS = ["gemini-3.1-flash-lite-preview", "gemini-2.5-flash", "gemini-2.0-flash"]
MAX_ATTEMPTS = 4
TEMPERATURE = 0.1
BUSINESS_RULES_PATH = "config/business_rules.yaml"
HISTORY_LIMIT = 20

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# Core Functions
# ============================================================

@st.cache_data(ttl=60) # Cache for 1 minute to balance hot-reloading and performance
def load_business_rules() -> Dict[str, Any]:
    """Load business rules from YAML file."""
    try:
        with open(BUSINESS_RULES_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load business rules: {str(e)}")
        # Provide minimal defaults if file loading fails
        return {
            "business_context": {"name": "AGEL Persona", "role": "Analyst"},
            "column_definitions": {},
            "calculation_rules": {},
            "output_format_contract": {"structure": {}}
        }

def extract_dynamic_schema(df: pd.DataFrame) -> str:
    """Extracts strictly present columns and categorical unique values from the dataset."""
    if df is None or df.empty:
        return "Dataset is currently empty or unavailable."
    
    schema = []
    schema.append(f"TOTAL ROWS: {len(df)}")
    schema.append("AVAILABLE COLUMNS: " + ", ".join(df.columns.tolist()))
    
    # Extract unique categories for context
    categorical_cols = ['Forecasting_Agency', 'State', 'Region', 'Transmission_Type', 'Access_Type', 'Plant_Type', 'Sub_Type']
    for col in categorical_cols:
        if col in df.columns:
            uniques = df[col].dropna().unique().tolist()
            # Trim if too many unique values
            if len(uniques) > 15:
                # E.g. Site_Name has too many, skip or summarize
                pass
            else:
                schema.append(f"UNIQUE {col}s: {uniques}")
                
    return "\n".join(schema)

def build_system_prompt(rules: Dict[str, Any], page_context: str = "Overall Portfolio", dynamic_schema: str = "") -> str:
    """Build the system instruction string entirely from business rules YAML and dynamic schema."""
    context = rules.get('business_context', {})
    cols = rules.get('column_definitions', {})
    calc = rules.get('calculation_rules', {})
    prioritization = rules.get('analysis_prioritization', {})
    tool_instructions = rules.get('tool_instructions', {})
    output_format = rules.get('output_format_contract', {})
    goal = rules.get('goal', 'Provide expert data-driven insights.')

    # Build output format structure section
    format_structure = output_format.get('structure', {})
    format_sections = "\n\n    ".join(format_structure.values()) if format_structure else ""

    # Build rules list
    format_rules = output_format.get('rules', [])
    rules_text = "\n    ".join(f"- {r}" for r in format_rules)

    # Build tool important rules
    tool_important_rules = tool_instructions.get('important_rules', [])
    tool_rules_text = "\n    ".join(f"{i+1}. {r}" for i, r in enumerate(tool_important_rules))

    prompt = f"""
    You are {context.get('name')}, a {context.get('role')}.
    
    BUSINESS CONTEXT:
    {yaml.dump(context.get('entities', {}))}
    
    CURRENT ANALYSIS FOCUS:
    You are specifically analyzing data for: {page_context}. 
    IF the user explicitly refers to their 'current selection', 'filtered data', 'selected filters', 'in this filter', etc., you MUST apply the active filters listed in the page context to `df` BEFORE running your analysis. 
    Treat the active filters as a dictionary where keys are column names and values are the lists of selected options. Use `df = df[df[col].isin(vals)]` for each filter. If a filter list is empty, ignore it. For general questions, analyze the full dataset without these filters.
    
    DYNAMIC DATAFRAME SCHEMA (CRITICAL - DO NOT HALLUCINATE COLUMNS OR CATEGORIES NOT LISTED HERE):
    {dynamic_schema}
    
    COLUMN DEFINITIONS:
    {yaml.dump(cols)}
    
    CALCULATION RULES:
    {yaml.dump(calc)}
    
    ANALYSIS PRIORITIZATION:
    {yaml.dump(prioritization)}
    
    GOAL: {goal}
    {tool_instructions.get('mandate', '')}
    
    DATA ACCESS:
    {tool_instructions.get('data_access', '')}
    
    IMPORTANT RULES FOR PYTHON TOOL:
    {tool_rules_text}
    
    OUTPUT FORMAT CONTRACT (MANDATORY):
    Your response MUST ALWAYS follow this exact structure:
    
    {format_sections}
    
    RULES:
    {rules_text}
    - Follow-up questions MUST be strictly related to the CURRENT ANALYSIS FOCUS ({page_context})
    """
    return prompt

# ============================================================
# Helper Analytics Functions
# ============================================================

def avc_weighted_average(df_subset: pd.DataFrame) -> float:
    if df_subset.empty or 'AVC_MW' not in df_subset.columns:
        return 0.0
    month_cols = MONTH_COLUMNS
    existing_months = [c for c in month_cols if c in df_subset.columns]
    if not existing_months: return 0.0
    
    total_avc = df_subset['AVC_MW'].sum()
    if total_avc == 0: return 0.0
    
    df_subset = df_subset.copy()
    df_subset['avg_penalty'] = df_subset[existing_months].mean(axis=1)
    return (df_subset['avg_penalty'] * df_subset['AVC_MW']).sum() / total_avc

def monthly_simple_average(df_subset: pd.DataFrame) -> float:
    month_cols = MONTH_COLUMNS
    existing_months = [c for c in month_cols if c in df_subset.columns]
    if not existing_months or df_subset.empty: return 0.0
    return df_subset[existing_months].mean().mean()

def portfolio_comparison(df_subset: pd.DataFrame) -> str:
    return "Comparison helper"

# ============================================================
# Tool Implementation
# ============================================================

def run_python_analysis(code: str, runtime_globals: Dict[str, Any]) -> str:
    try:
        tree = ast.parse(code)
    except Exception as e:
        return f"TOOL_ERROR: Invalid Python syntax: {e}"

    # Use a Blacklist approach to allow normal Pandas/Python idioms but block OS/File operations
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "Error: Import statements are restricted for security."
        
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ['open', 'exec', 'eval', '__import__', 'exit', 'quit', 'sys', 'os', 'subprocess']:
                    return f"Error: Calling global function '{func_name}' is not allowed."
                
            # Block attribute calls like os.system or subprocess.run
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id in ['os', 'sys', 'subprocess', 'shutil', 'pathlib']:
                    return f"Error: Module '{node.func.value.id}' is restricted."

    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, runtime_globals)
            
        res = output.getvalue().strip()
        if not res:
            return "Code executed successfully but printed no output. You MUST use print() or display() to see the results."
        return res
    except Exception as e:
        return f"TOOL_ERROR: {str(e)}"

def prepare_tool_runtime(df: pd.DataFrame) -> Dict[str, Any]:
    def portfolio_comparison_local(subset: pd.DataFrame) -> str:
        subset_val = avc_weighted_average(subset)
        total_val = avc_weighted_average(df)
        diff = subset_val - total_val
        status = "higher" if diff > 0 else "lower"
        return f"Subset penalty ({subset_val:.2f}) is {abs(diff):.2f} ps/kWh {status} than portfolio average ({total_val:.2f})."

    return {
        'df': df,
        'pd': pd,
        'avc_weighted_average': avc_weighted_average,
        'monthly_simple_average': monthly_simple_average,
        'portfolio_comparison': portfolio_comparison_local
    }



@st.cache_resource
def initialize_gemini_client() -> Optional[genai.Client]:
    """Initialize client using Streamlit secrets."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None
    return genai.Client(api_key=api_key)

def execute_ai_query(
    client: genai.Client,
    model_id: str,
    system_instruction: str,
    prompt: str,
    history: List[Dict[str, str]],
    runtime_globals: Dict[str, Any],
    status_callback: Optional[Callable] = None
) -> Tuple[str, str]:
    """Execute query with fallback and tool support."""
    
    def run_python_analysis_tool(python_code: str) -> str:
        """
        Executes Python code to analyze the 'df' DataFrame. Use this for ALL numerical calculations.
        Available: df (DataFrame), avc_weighted_average(df), monthly_simple_average(df), portfolio_comparison(df).
        """
        if status_callback:
            status_callback("Executing Pandas Data Analysis...")
        result = run_python_analysis(python_code, runtime_globals)
        if status_callback:
            status_callback("Synthesizing final insights...")
        return result
    
    # Convert history
    formatted_history = []
    for msg in history[-HISTORY_LIMIT:]:
        role = "model" if msg["role"] == "assistant" else "user"
        content = msg.get("content", "")
        if content:
            formatted_history.append(types.Content(role=role, parts=[types.Part.from_text(text=str(content))]))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=TEMPERATURE,
        tools=[run_python_analysis_tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=10
        )
    )

    last_error = None
    current_model = model_id
    
    for attempt in range(MAX_ATTEMPTS):
        try:
            if status_callback:
                status_callback("Reading prompt and accessing model...")
                
            chat = client.chats.create(model=current_model, config=config, history=formatted_history)
            current_input = prompt
            
            try:
                # The SDK automatically handles the tool loop natively! 
                response = chat.send_message(prompt)
                
                if response.text:
                    yield response.text
                    return
                else:
                    # Check if response ended with a function call (AFC limit exhausted)
                    has_function_calls = any(
                        hasattr(part, 'function_call') and part.function_call 
                        for part in (response.candidates[0].content.parts if response.candidates else [])
                    )
                    if has_function_calls:
                        yield (
                            "I wasn't able to find the exact data you're looking for after multiple attempts. "
                            "This usually means the term or category you mentioned doesn't exist in the dataset. "
                            "Could you rephrase your question or check the available categories in the schema above?\n\n"
                            "FOLLOW_UP: What site names are available in the dataset?\n"
                            "FOLLOW_UP: Show me available categories and columns.\n"
                            "FOLLOW_UP: What data is available for Khavda?"
                        )
                    else:
                        yield "\n\n*Error: API responded successfully, but returned an empty text string.*"
                    return

            except Exception as stream_e:
                logger.error(f"Execution error: {stream_e}")
                raise stream_e

        except Exception as e:
            import traceback
            logger.error(f"Full Exception in Gemini Query: {traceback.format_exc()}")
            err_str = str(e).lower()
            infra_errors = ["rate limit", "unavailable", "internal", "timeout", "exhausted", "500", "503", "429"]
            
            if any(err in err_str for err in infra_errors):
                logger.warning(f"Infra error on {current_model}: {str(e)}. Retrying...")
                last_error = e
                if attempt < len(MODEL_FALLBACKS):
                    current_model = MODEL_FALLBACKS[attempt]
                continue
            else:
                yield f"\n### Error\nAn error occurred during analysis: `{type(e).__name__}`.\n\nPlease try a different query or click retry."
                return

    yield f"\n### Error\nFailed after {MAX_ATTEMPTS} attempts due to infrastructure issues: `{last_error}`."
    return

# ============================================================
# Public API
# ============================================================

def get_gemini_response(prompt: str, df: pd.DataFrame, history: List[Dict[str, str]] = None, page_context: str = "Overall Portfolio", status_callback: Optional[Callable] = None):
    """Main Streamlit entry point. Returns a generator yielding string chunks."""
    if history is None: history = []
    
    # Support backward compatibility if context string is passed instead of df
    if not isinstance(df, pd.DataFrame):
        # If df is not a dataframe, try to find it in session state or usage might be mismatched
        # This is a safety net
        if "df" in st.session_state:
            df = st.session_state.df
        else:
            yield "Internal Error: Dataset not found in tool runtime."
            return

    rules = load_business_rules()
    
    dynamic_schema = extract_dynamic_schema(df)
    system_instruction = build_system_prompt(rules, page_context=page_context, dynamic_schema=dynamic_schema)
    client = initialize_gemini_client()
    
    if not client:
        yield "Authentication Error: Gemini API Key missing or invalid."
        return
    
    runtime_globals = prepare_tool_runtime(df)
    
    yield from execute_ai_query(
        client, MODEL_PRIMARY, system_instruction, prompt, history, runtime_globals, status_callback=status_callback
    )

def prepare_ai_context(df: pd.DataFrame, df_long: pd.DataFrame = None) -> Any:
    """Return the dataframe to be stored as context for get_gemini_response."""
    return df
