"""
CSV logging for marketplace sumulation
writes data in CSV format in append mode
"""
import csv
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

class CSVLogger:
    """
    write csv files for marketplace simulation
    """

    def __init__(self, output_dir:str = "simulation_data"):
        """
        initialize logger
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    
    def _write_csv(self, filename:str, data: Dict[str, Any], fieldnames:List[str]):
        """ 
        write data to csv file
        """
        filepath = self.output_dir / filename
        file_exists = filepath.exists()

        with open(filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # write header if file does not exist
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data)
        
    
    def log_transactions(self, simulation_id:str, cycle:int, transaction_data:Dict[str, Any]):
        """
        log transaction data
        """
        fieldnames = [
            'simulation_id', 'timestamp', 'cycle', 'transaction_id',
            'buyer_id', 'buyer_archetype', 'seller_id', 'seller_archetype',
            'product_name', 'category', 'listing_price', 'final_price',
            'profit', 'margin', 'negotiation_rounds'
        ]

        data = {
            'simulation_id': simulation_id,
            'timestamp': datetime.now().isoformat(),
            'cycle': cycle,
            **transaction_data,
            }
        
        self._write_csv('transactions.csv', data, fieldnames)

    
    def log_negotiation(self, simulation_id:str, cycle:int, negotiation_data:Dict[str, Any]):
        """
        log negotiation data
        """
        fieldnames = [
            'simulation_id', 'timestamp', 'cycle', 'negotiation_id',
            'buyer_id', 'seller_id', 'product_name', 'listing_price',
            'initial_offer', 'final_offer', 'outcome', 'rounds', 'action'
        ]

        data = {
            'simulation_id': simulation_id, 
            'timestamp': datetime.now().isoformat(),
            'cycle': cycle,
            **negotiation_data,
        }

        self._write_csv('negotiations.csv', data, fieldnames)

    def log_agent_state(self, simulation_id:str, cycle:int, agent_data:Dict[str, Any]):
        """
        log agent state data
        """

        fieldnames = [
            'simulation_id', 'timestamp', 'cycle', 'agent_id', 'name',
            'archetype', 'capital', 'inventory_count', 'inventory_value',
            'total_sales', 'total_purchases', 'total_profit', 'total_assets'
        ]

        data = {
            'simulation_id': simulation_id,
            'timestamp': datetime.now().isoformat(),
            'cycle': cycle,
            **agent_data,
        }

        self._write_csv('agent_state.csv', data, fieldnames)

    
    def log_market_metrics(self, simulation_id:str, cycle:int, metrics_data:Dict[str, Any]):
        """
        log metrics data
        """
        fieldnames = [
            'simulation_id', 'timestamp', 'cycle', 'active_listings',
            'total_transactions', 'total_volume', 'avg_transaction_price',
            'categories_listed', 'total_profit', 'avg_margin'
        ]

        data = {
            'simulation_id': simulation_id,
            'timestamp': datetime.now().isoformat(),
            'cycle': cycle,
            **metrics_data,
        }

        self._write_csv('metrics.csv', data, fieldnames)


    def log_listing(self, simulation_id:str, cycle:int, listing_data:Dict[str, Any]):
        """
        log listing data
        """
        fieldnames = [
            'simulation_id', 'timestamp', 'cycle', 'listing_id',
            'seller_id', 'product_name', 'category', 'listing_price',
            'minimum_acceptable', 'status', 'reasoning_summary'
        ]

        data = {
            'simulation_id': simulation_id,
            'timestamp': datetime.now().isoformat(),
            'cycle': cycle,
            **listing_data,
        }

        self._write_csv('listings.csv', data, fieldnames)

    

