"""
utilities to initialize agents inventory
"""
import random
from typing import List
from models.data_models import Product, InventoryItem,AgentArchetype
from config.settings import settings

def generate_product_name(category:str)->str:
    """
    generate a specific product name for a acategory
    
    Args:
        category: product category
    Returns:
        product name
    """
    product_names = {
        "Electronics": [
            "Laptop_Dell_XPS", "Laptop_HP_Pavilion", "Tablet_iPad_Air",
            "Smartphone_Galaxy", "Headphones_Sony", "Monitor_LG_27"
        ],
        "Furniture": [
            "Chair_Office_Ergonomic", "Desk_Standing", "Sofa_Leather",
            "Table_Dining_Oak", "Bookshelf_Modern", "Lamp_Floor"
        ],
        "Collectibles": [
            "Baseball_Card_Vintage", "Comic_Book_Rare", "Coin_Gold",
            "Stamp_Collection", "Action_Figure_Limited", "Poster_Signed"
        ],
        "Appliances": [
            "Microwave_Samsung", "Blender_Vitamix", "Coffee_Maker_Pro",
            "Vacuum_Dyson", "Air_Purifier", "Dishwasher_Bosch"
        ],
        "Tools": [
            "Drill_DeWalt_Cordless", "Saw_Circular", "Wrench_Set",
            "Hammer_Professional", "Toolbox_Complete", "Sander_Orbital"
        ],
        "Sports_Equipment": [
            "Tennis_Racket_Wilson", "Basketball_Spalding", "Yoga_Mat_Premium",
            "Weights_Dumbbell_Set", "Bike_Mountain", "Skateboard_Pro"
        ]
    }

    names = product_names.get(category, [f"{category}_Item"])
    return random.choice(names) + f"_{random.randint(100, 999)}"


def create_initial_inventory(
        agent_archetype:AgentArchetype, 
        num_items: int 
        ) -> List[InventoryItem]:
    """
    create initial inventory for an agent based on archetype
    Args:
        agent_achetype:  agent's personality
        num_items: num items in inventory
    Returns:
        list of inventory items
    """
    if num_items is None:
        num_items =  settings.initial_inventory_size

    invetory = []
    categories = list(settings.product_categories.keys())

    # specialists focused on 1 or 2 categories
    if agent_archetype == AgentArchetype.SPECIALIST:
        categories = random.sample(categories, k=min(2,len(categories)))

    for _ in range(num_items):
        # pick category
        category = random.choice(categories)
        base_value = settings.product_categories[category]

        # create product
        product = Product(
            name=generate_product_name(category),
            category=category,
            base_market_value=base_value
        )

        cost_multipliers = {
            AgentArchetype.OPPORTUNIST: (0.60, 0.70),      
            AgentArchetype.SPECIALIST: (0.65, 0.75),        
            AgentArchetype.AGGRESSIVE_TRADER: (0.70, 0.80), 
            AgentArchetype.CONSERVATIVE: (0.75, 0.85),      
            AgentArchetype.PATIENT_INVESTOR: (0.70, 0.80),
            AgentArchetype.RISK_TAKER: (0.65, 0.85),        
            AgentArchetype.EMOTIONAL: (0.70, 0.85),
            AgentArchetype.DATA_DRIVEN: (0.68, 0.78),
            AgentArchetype.SOCIAL: (0.72, 0.82),
            AgentArchetype.CHAOTIC: (0.60, 0.90),       
        }

        multiplier_range = cost_multipliers.get(agent_archetype, (0.70, 0.80))
        cost_basis = base_value * random.uniform(*multiplier_range)

        invetory.append(InventoryItem(product=product, cost_basis=cost_basis))
    
    return invetory


def initialize_agent_inventory(agent)->List[InventoryItem]:
    """
    initialize invetory to agent add to state
    Args:
        agent: agent to initialize
    Returns:
        list of inventory items
    """
    inventory = create_initial_inventory(agent.state.archetype)
    agent.state.inventory = inventory
    print(f"{agent.state.name} inventory initialized: {len(inventory)} items")
    for item in inventory:
        print(f" - {item.product.name}: ${item.cost_basis:.2f}")

    return inventory

