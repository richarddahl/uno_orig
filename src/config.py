import os

from pathlib import Path

from typing import Type

from pydantic_settings import BaseSettings, SecretsSettingsSource, SettingsConfigDict


class General(BaseSettings):
    # GENERAL SETTINGS
    SITE_NAME: str
    DEBUG: bool = True
    LOCALE: str = "en_US"
    ENV: str = "dev"

    # DATABASE SETTINGS
    DB_USER_PW: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_SCHEMA: str
    DB_DRIVER: str
    DB_URL: str

    # AUDITING SETTINGS
    DB_AUDITED_TABLES: list

    # DATABASE QUERY SETTINGS
    DEFAULT_LIMIT: int = 100
    DEFAULT_OFFSET: int = 0
    DEFAULT_PAGE_SIZE: int = 25

    # SECURITY SETTINGS
    # jwt related settings
    TOKEN_EXPIRE_MINUTES: int = 15
    TOKEN_REFRESH_MINUTES: int = 30
    TOKEN_ALGORITHM: str = "HS256"
    TOKEN_SECRET_KEY: str
    LOGIN_URL: str

    # password related settings
    PASSWORD_MIN_LENGTH: int = 10
    PASSWORD_MAX_LENGTH: int = 120
    PASSWORD_MIN_UPPERCASE: int = 1
    PASSWORD_MIN_LOWERCASE: int = 1
    PASSWORD_MIN_DIGITS: int = 1
    PASSWORD_MIN_SPECIAL: int = 1
    PASSWORD_PERSONAL_INFO_SUBSTRING_LENGTH: int = 3
    PASSWORD_HISTORY_LENGTH: int = 10

    # APPLICATION SETTINGS
    # Max Groups and Users for each type of customer
    MAX_INDIVIDUAL_GROUPS: int = 1
    MAX_INDIVIDUAL_USERS: int = 1
    MAX_SMALL_BUSINESS_GROUPS: int = 5
    MAX_SMALL_BUSINESS_USERS: int = 5
    MAX_CORPORATE_GROUPS: int = 25
    MAX_CORPORATE_USERS: int = 25
    MAX_ENTERPRISE_GROUPS: int = -1
    MAX_ENTERPRISE_USERS: int = -1

    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(General):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Test(General):
    ENV: str = "test"
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


env_settings: dict[str, Type[General]] = {"dev": Dev, "test": Test}
settings: Dev | Test = env_settings[os.environ.get("ENV", "dev").lower()]()
