# cmbagent/utils.py
import os
import autogen
import pickle
import logging
from ruamel.yaml import YAML
from autogen.cmbagent_utils import cmbagent_debug
from pathlib import Path
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')

cmbagent_debug = autogen.cmbagent_debug



# Get the path of the current file (go up one level from utils/ to cmbagent/)
path_to_basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if cmbagent_debug:
    print('path_to_basedir: ', path_to_basedir)

# Construct the path to the APIs directory
path_to_apis = os.path.join(path_to_basedir, "apis")
if cmbagent_debug:
    print('path_to_apis: ', path_to_apis)

# Removed path_to_assistants as RAG agents have been removed
path_to_agents = os.path.join(path_to_basedir, "agents/")

# path_to_engineer = os.path.join(path_to_basedir, "engineer")
# path_to_planner = os.path.join(path_to_basedir, "planner")
# path_to_executor = os.path.join(path_to_basedir, "executor")
# path_to_admin = os.path.join(path_to_basedir, "admin")

if "site-packages" in path_to_basedir or "dist-packages" in path_to_basedir:
    work_dir_default = os.path.join(os.getcwd(), "cmbagent_output")
else:
    work_dir_default = os.path.join(path_to_basedir, "../output")


work_dir_default = Path(work_dir_default).expanduser().resolve()

if cmbagent_debug:
    print('\n\n\n\n\nwork_dir_default: ', work_dir_default)


default_chunking_strategy = {
    "type": "static",
    "static": {
        "max_chunk_size_tokens": 200, # reduce size to ensure better context integrity
        "chunk_overlap_tokens": 100 # increase overlap to maintain context across chunks
    }
}

# notes from https://platform.openai.com/docs/assistants/tools/file-search:

# max_chunk_size_tokens must be between 100 and 4096 inclusive.
# chunk_overlap_tokens must be non-negative and should not exceed max_chunk_size_tokens / 2.

# By default, the file_search tool outputs up to 20 chunks for gpt-4* models and up to 5 chunks for gpt-3.5-turbo. 
# You can adjust this by setting file_search.max_num_results in the tool when creating the assistant or the run.

default_top_p = 0.05
default_temperature = 0.00001


default_select_speaker_prompt_template = """
Read the above conversation. Then select the next role from {agentlist} to play. Only return the role.
Note that only planner can modify or update the PLAN. planner should not be selected after the PLAN has been approved.
executor should not be selected unless admin says "execute".
engineer should be selected to check for conflicts. 
engineer should be selected to check code. 
engineer should be selected to provide code to save summary of session. 
executor should be selected to execute. 
planner should be the first agent to speak. 
"""
### note that we hardcoded the requirement that planner speaks first. 


default_select_speaker_message_template = """
You are in a role play game about cosmological data analysis. The following roles are available:
                {roles}.
                Read the following conversation.
                Then select the next role from {agentlist} to play. Only return the role.
Note that only planner can modify or update the PLAN.
planner should not be selected after the PLAN has been approved.
executor should not be selected unless admin says "execute".
engineer should be selected to check for conflicts. 
engineer should be selected to check code. 
executor should be selected to execute. 
planner should be the first agent to speak.
"""


default_groupchat_intro_message = """
We have assembled a team of LLM agents and a human admin to solve Cosmological data analysis tasks. 

In attendance are:
"""

# TODO
# see https://github.com/openai/openai-python/blob/da48e4cac78d1d4ac749e2aa5cfd619fde1e6c68/src/openai/types/beta/file_search_tool.py#L20
# default_file_search_max_num_results = 20
# The default is 20 for `gpt-4*` models and 5 for `gpt-3.5-turbo`. This number
# should be between 1 and 50 inclusive.
file_search_max_num_results = autogen.file_search_max_num_results

default_max_round = 50

# default_llm_model = 'gpt-4o-2024-11-20'
default_llm_model = 'gpt-4.1-2025-04-14'
# default_llm_model = 'gpt-4o-mini'
# default_llm_model = "gemini-2.0-flash"
default_formatter_model = 'o3-mini-2025-01-31'





# hep-theory fork: all-Anthropic defaults (was hardcoded to OpenAI models).
# Fable 5 for planning/idea-generation roles (exploratory, long-context synthesis);
# Sonnet for execution/critique roles; Haiku for mechanical formatting.
default_agents_llm_model = {
    "engineer": "claude-sonnet-5",
    "aas_keyword_finder": "claude-haiku-4-5-20251001",
    "researcher": "claude-sonnet-5",
    "planner": "claude-fable-5",
    "plan_reviewer": "claude-sonnet-5",
    "idea_hater": "claude-fable-5",
    "idea_maker": "claude-fable-5",
    "camb_context": "claude-sonnet-5",
    "summarizer": "claude-haiku-4-5-20251001",
    "summarizer_response_formatter": "claude-haiku-4-5-20251001",
    "inspirehep_context": "claude-sonnet-5",
    "cadabra_context": "claude-sonnet-5",
    "derivation_checker": "claude-sonnet-5",
}

default_agent_llm_configs = {}

# Local / OSS model endpoints (model name -> base URL)
# Add your vLLM or other OpenAI-compatible servers here.
# Set the corresponding environment variables (e.g. GPT_OSS_120B_URL).
local_llm_urls = {
    "gpt-oss-120b": os.getenv("GPT_OSS_120B_URL"),
    # "gpt-oss-20b": os.getenv("GPT_OSS_20B_URL"),
}

def get_api_keys_from_env():
    api_keys = {
        "OPENAI" : os.getenv("OPENAI_API_KEY"),
        "GEMINI" : os.getenv("GEMINI_API_KEY"),
        "ANTHROPIC" : os.getenv("ANTHROPIC_API_KEY"),
        "MISTRAL" : os.getenv("MISTRAL_API_KEY"),
    }
    return api_keys


def get_model_config(model, api_keys):
    # Allow passing a full config dict (e.g. for local LLM with base_url)
    if isinstance(model, dict):
        return model

    config = {
        "model": model,
        "api_key": None,
        "api_type": None
    }

    # Check local_llm_urls registry first
    local_url = local_llm_urls.get(model)
    if local_url:
        config.update({
            "base_url": local_url.rstrip("/"),
            "api_key": os.getenv("LOCAL_LLM_API_KEY", "EMPTY"),
            "api_type": "openai",
            "price": [0.0, 0.0],
        })
        return config

    # Known cloud providers
    if 'o3' in model or 'o1' in model:
        config.update({
            "reasoning_effort": "medium",
            "api_key": api_keys["OPENAI"],
            "api_type": "openai"
        })
    elif "gemini" in model:
        config.update({
            "api_key": api_keys["GEMINI"],
            "api_type": "google"
        })
    elif "claude" in model:
        config.update({
            "api_key": api_keys["ANTHROPIC"],
            "api_type": "anthropic"
        })
    else:
        config.update({
            "api_key": api_keys["OPENAI"],
            "api_type": "openai"
        })
    return config

api_keys_env = get_api_keys_from_env()

# print('api_keys_env: ', api_keys_env)

for agent in default_agents_llm_model:
    default_agent_llm_configs[agent] =  get_model_config(default_agents_llm_model[agent], api_keys_env)


default_llm_config_list = [get_model_config(default_llm_model, api_keys_env)]


#### note we should be able to set the temperature for different agents, e.g., 
                    # "idea_maker": {
                    #     "model": default_llm_model,
                    #     "api_key": os.getenv("OPENAI_API_KEY"),
                    #     "api_type": "openai",
                    #     'temperature': 0.5,
                    #     },



def update_yaml_preserving_format(yaml_file, agent_name, new_id, field = 'vector_store_ids'):
    yaml = YAML()
    yaml.preserve_quotes = True  # This preserves quotes in the YAML file if they are present

    # Load the YAML file while preserving formatting
    with open(yaml_file, 'r') as file:
        yaml_content = yaml.load(file)
    
    # Update the vector_store_id for the specific agent
    if yaml_content['name'] == agent_name:
        if field == 'vector_store_ids':
            yaml_content['assistant_config']['tool_resources']['file_search']['vector_store_ids'][0] = new_id
        elif field == 'assistant_id':
            yaml_content['assistant_config']['assistant_id'] = new_id
    else:
        print(f"Agent {agent_name} not found.")
    
    # Write the changes back to the YAML file while preserving formatting
    with open(yaml_file, 'w') as file:
        yaml.dump(yaml_content, file)

def aas_keyword_to_url(keyword):
    """
    Given an AAS keyword, return its IAU Thesaurus URL.
    
    Args:
        keyword (str): The AAS keyword (e.g., "H II regions")
        
    Returns:
        str: The corresponding IAU Thesaurus URL
    """
    with open('aas_kwd_to_url.pkl', 'rb') as f:
        dic = pickle.load(f)
    return dic[keyword]


# Keywords are in the utils/keywords directory
keywords_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keywords')

with open(os.path.join(keywords_dir, 'aas_kwd_to_url.pkl'), 'rb') as file:
    AAS_keywords_dict = pickle.load(file)

# print(my_dict)
# Assuming you have already loaded your dictionary into `my_dict`
AAS_keywords_string = ', '.join(AAS_keywords_dict.keys())

unesco_taxonomy_path = os.path.join(keywords_dir, 'unesco_hierarchical.json')
aaai_keywords_path = os.path.join(keywords_dir, 'aaai.md')

camb_context_url = "https://camb.readthedocs.io/en/latest/_static/camb_docs_combined.md"



def clean_llm_config(llm_config):
    config = llm_config['config_list'][0]
    api_type = config.get('api_type')
    model = config.get('model', '')

    # Remove base_url for cloud APIs (anthropic, google) to prevent pollution from OSS model defaults
    # Only keep base_url for local/OSS models (openai api_type with model in local_llm_urls)
    if api_type in ('anthropic', 'google'):
        config.pop('base_url', None)
    elif api_type == 'openai' and 'base_url' in config:
        # Check if this is actually a local model - if not, remove base_url
        if model not in local_llm_urls:
            config.pop('base_url', None)

    if "reasoning_effort" in config:
        if 'temperature' in llm_config:
            llm_config.pop('temperature')
        if 'top_p' in llm_config:
            llm_config.pop('top_p')


    # Pop temperature if using GPT-5 model
    if 'gpt-5' in model:
        if 'temperature' in llm_config:
            llm_config.pop('temperature', None)
        if 'top_p' in llm_config:
            llm_config.pop('top_p', None)

    # print('\nin cmbagent.py: llm_config: ', llm_config)



    if api_type == 'google':
        if 'top_p' in llm_config:
            llm_config.pop('top_p')

def fetch_local_model_name(base_url: str, api_key: str) -> str:
    """
    Fetch the locally served model name using a request

    Args:
        base_url: The base url to target
        api_key: The API key to use

    Returns:
        Model name as a string e.g. 'openai/gpt-oss-20b'
    """
    r = requests.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    r.raise_for_status()
    models = r.json().get("data", [])
    if not models:
        raise RuntimeError("No models found at endpoint")
    return models[0]["id"]


def get_local_llm_config(base_url=None, api_key=None, model=None):
    """
    Build a config dict for a local/OSS LLM server (e.g. vLLM).

    Reads from environment variables by default:
        LOCAL_LLM_BASE_URL  – server URL  (e.g. http://orion:8010/v1)
        LOCAL_LLM_API_KEY   – API key     (default: "EMPTY")

    If ``model`` is not given, the model name is auto-discovered
    from the server's /models endpoint.

    Returns:
        dict ready to pass as ``engineer_model`` etc.
    """
    base_url = (base_url or os.getenv("LOCAL_LLM_BASE_URL", "")).rstrip("/")
    if not base_url:
        raise ValueError(
            "No local LLM URL provided. "
            "Set LOCAL_LLM_BASE_URL or pass base_url explicitly."
        )
    api_key = api_key or os.getenv("LOCAL_LLM_API_KEY", "EMPTY")

    if model is None:
        model = fetch_local_model_name(base_url, api_key)

    return {
        "model": model,
        "api_key": api_key,
        "api_type": "openai",
        "base_url": base_url,
        "price": [0.0, 0.0],
    }