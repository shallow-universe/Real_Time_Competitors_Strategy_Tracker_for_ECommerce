import streamlit_authenticator as stauth
from streamlit_authenticator import Hasher
import yaml
from yaml.loader import SafeLoader

def create_user_config():
    """Create initial user configuration"""
    # Hash passwords
    passwords = ['admin123', 'analyst123']
    hashed_passwords = Hasher(passwords).generate()
    
    config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@example.com',
                    'name': 'Administrator',
                    'password': hashed_passwords[0]
                },
                'analyst': {
                    'email': 'analyst@example.com', 
                    'name': 'Data Analyst',
                    'password': hashed_passwords[1]
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'competitor_tracker_key',
            'name': 'competitor_tracker_cookie'
        },
        'preauthorized': {
            'emails': []
        }
    }
    
    return config

def get_authenticator():
    config = create_user_config()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )
    return authenticator