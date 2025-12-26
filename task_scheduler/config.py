"""Configuration management for scheduling rules."""
from dotenv import load_dotenv
load_dotenv()

from dataclasses import dataclass, field
from datetime import time
from typing import Optional
import yaml


@dataclass
class SchedulingConfig:
    """Configuration for scheduling rules and parameters."""
    timezone: str = "Africa/Addis_Ababa"
    fairness_window_days: int = 90
    
    # ATM scheduling rules
    atm_rest_rule_enabled: bool = True  # B-shift gets next day off
    atm_morning_window_start: time = time(6, 0)
    atm_morning_window_end: time = time(8, 30)
    atm_midday_window_start: time = time(8, 30)
    atm_midday_window_end: time = time(14, 30)
    atm_night_window_start: time = time(14, 30)
    atm_night_window_end: time = time(22, 0)
    
    # Cooldown rules (avoid consecutive heavy shifts)
    atm_b_cooldown_days: int = 2  # Minimum days between B-shift assignments
    
    # SysAid rules
    sysaid_week_start_day: int = 0  # 0=Monday, 6=Sunday
    
    @classmethod
    def from_yaml(cls, file_path: str) -> "SchedulingConfig":
        """Load configuration from YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = cls()
        
        if 'timezone' in data:
            config.timezone = data['timezone']
        if 'fairness_window_days' in data:
            config.fairness_window_days = data['fairness_window_days']
        
        if 'atm' in data:
            atm = data['atm']
            if 'rest_rule_enabled' in atm:
                config.atm_rest_rule_enabled = atm['rest_rule_enabled']
            if 'b_cooldown_days' in atm:
                config.atm_b_cooldown_days = atm['b_cooldown_days']
            if 'windows' in atm:
                w = atm['windows']
                if 'morning' in w:
                    config.atm_morning_window_start = time(*map(int, w['morning']['start'].split(':')))
                    config.atm_morning_window_end = time(*map(int, w['morning']['end'].split(':')))
                if 'midday' in w:
                    config.atm_midday_window_start = time(*map(int, w['midday']['start'].split(':')))
                    config.atm_midday_window_end = time(*map(int, w['midday']['end'].split(':')))
                if 'night' in w:
                    config.atm_night_window_start = time(*map(int, w['night']['start'].split(':')))
                    config.atm_night_window_end = time(*map(int, w['night']['end'].split(':')))
        
        if 'sysaid' in data:
            sysaid = data['sysaid']
            if 'week_start_day' in sysaid:
                config.sysaid_week_start_day = sysaid['week_start_day']
        
        return config

