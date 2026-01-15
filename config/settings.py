import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # WordPress
    wordpress_url: str = Field(validation_alias='WP_SITE_URL')
    wordpress_username: str = Field(validation_alias='WP_USERNAME')
    wordpress_app_password: str = Field(validation_alias='WP_APP_PASSWORD')
    
    # WooCommerce (Optional)
    woocommerce_consumer_key: str = ""
    woocommerce_consumer_secret: str = ""
    
    # Gemini
    gemini_api_key: str
    
    # LanceDB
    lancedb_path: str = "./data/lancedb"
    
    # Environment
    environment: str = "development"
    
    # Project Mode
    project_mode: str = "production" 
    
    # Brand Info
    brand_name: str = "FUNIT"

    model_config = SettingsConfigDict(
        env_file=['.env'],
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Global settings instance
settings = Settings()
