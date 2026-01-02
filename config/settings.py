"""
configurations for markeplace simulation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List
import os
from dotenv import load_dotenv


# load env. variables
load_dotenv()

class Settings(BaseSettings):

    # initialize Gemini
    PROJECT_ID: str = os.getenv("GCLOUD_PROJECT_ID_VM", "cvm-deploy-vm")
    LOCATION:str = "us-central1"
    GEMINI_MODEL:str = "gemini-2.5-flash"
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    #OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
                                    

    # simulation settings
    num_agents: int = 7
    MAX_NEGOTIATION_ROUNDS : int = 5

    # agentes archetypes
    agent_archetypes: List[str] = [
        'Agressive_Trader', 
        'Patient_Investor', 
        'Opportunist',
        'Risk_Taker', 
        'Conservative',
        'Specialist', 
        'Emotional', 
        'Data_Driven', 
        'Social', 
        'Chaotic'
    ]

    # product categories
    product_categories: Dict[str, float] = {
        'Eletronics': 1000.0,
        'Furniture': 500.0,
        'Collectibles': 800.0,
        'Appliances':600.0,
        'Tools':400.0,
        'Sports_Equipment':300.0
    }

    # market configuration
    initial_capital_per_agent: float = 5000.0
    initial_inventory_size: int = 3

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
# global setting instance
settings = Settings()

print('Settings loaded successfully')
print(f" Model: {settings.GEMINI_MODEL}")
print(f" Temperature: {settings.TEMPERATURE}")
print(f" Number of agents: {len(settings.agent_archetypes)}")
    

