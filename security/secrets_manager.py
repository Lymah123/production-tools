#!/usr/bin/env python3
"""
Secrets Manager
Unified interface for AWS Secrets Manager & HashiCorp Vault
Supports encryption, retrieval, and rotation of secrets
"""

import os
import sys
import json
import click
from pathlib import Path
from typing import Dict, Optional, Any
from rich.console import Console
from rich.table import Table
from rich import box
import logging

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# BACKEND INTERFACES
# ──────────────────────────────────────────────────────────────
class SecretsBackend:
    """Base class for secrets backends"""
    
    def get_secret(self, name: str) -> Optional[Dict]:
        raise NotImplementedError
    
    def put_secret(self, name: str, value: Dict) -> bool:
        raise NotImplementedError
    
    def list_secrets(self) -> list:
        raise NotImplementedError
    
    def delete_secret(self, name: str) -> bool:
        raise NotImplementedError


class AWSSecretsBackend(SecretsBackend):
    """AWS Secrets Manager backend"""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        try:
            import boto3
            self.client = boto3.client('secretsmanager', region_name=region)
            logger.info(f"AWS Secrets Manager connected (region: {region})")
        except Exception as e:
            logger.error(f"AWS connection failed: {e}")
            self.client = None
    
    def get_secret(self, name: str) -> Optional[Dict]:
        if not self.client:
            return None
        
        try:
            response = self.client.get_secret_value(SecretId=name)
            secret_string = response.get('SecretString')
            return json.loads(secret_string) if secret_string else None
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret not found: {name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret {name}: {e}")
            return None
    
    def put_secret(self, name: str, value: Dict) -> bool:
        if not self.client:
            return False
        
        try:
            secret_string = json.dumps(value)
            
            # Try to update existing secret
            try:
                self.client.update_secret(
                    SecretId=name,
                    SecretString=secret_string
                )
                logger.info(f"Updated secret: {name}")
            except self.client.exceptions.ResourceNotFoundException:
                # Create new secret
                self.client.create_secret(
                    Name=name,
                    SecretString=secret_string
                )
                logger.info(f"Created secret: {name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to put secret {name}: {e}")
            return False
    
    def list_secrets(self) -> list:
        if not self.client:
            return []
        
        try:
            response = self.client.list_secrets()
            return [s['Name'] for s in response.get('SecretList', [])]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    def delete_secret(self, name: str) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.delete_secret(
                SecretId=name,
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"Deleted secret: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False


class VaultBackend(SecretsBackend):
    """HashiCorp Vault backend"""
    
    def __init__(self, url: str = "http://127.0.0.1:8200", token: str = None):
        self.url = url
        self.token = token or os.getenv("VAULT_TOKEN")
        
        try:
            import hvac
            self.client = hvac.Client(url=url, token=self.token)
            
            if self.client.is_authenticated():
                logger.info(f"Vault connected: {url}")
            else:
                logger.warning("Vault authentication failed")
                self.client = None
        except ImportError:
            logger.error("hvac package not installed. Run: pip install hvac")
            self.client = None
        except Exception as e:
            logger.error(f"Vault connection failed: {e}")
            self.client = None
    
    def get_secret(self, name: str) -> Optional[Dict]:
        if not self.client:
            return None
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=name)
            return response['data']['data']
        except Exception as e:
            logger.error(f"Failed to get secret {name}: {e}")
            return None
    
    def put_secret(self, name: str, value: Dict) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=name,
                secret=value
            )
            logger.info(f"Stored secret in Vault: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to put secret {name}: {e}")
            return False
    
    def list_secrets(self) -> list:
        if not self.client:
            return []
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(path='')
            return response['data']['keys']
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    def delete_secret(self, name: str) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=name)
            logger.info(f"Deleted secret: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False


# ──────────────────────────────────────────────────────────────
# SECRETS MANAGER
# ──────────────────────────────────────────────────────────────
class SecretsManager:
    """Unified secrets management interface"""
    
    def __init__(self, backend: str = "aws", **kwargs):
        self.backend_type = backend
        
        if backend == "aws":
            self.backend = AWSSecretsBackend(**kwargs)
        elif backend == "vault":
            self.backend = VaultBackend(**kwargs)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
    
    def get(self, name: str) -> Optional[Dict]:
        """Retrieve a secret"""
        return self.backend.get_secret(name)
    
    def put(self, name: str, value: Dict) -> bool:
        """Store a secret"""
        return self.backend.put_secret(name, value)
    
    def list(self) -> list:
        """List all secrets"""
        return self.backend.list_secrets()
    
    def delete(self, name: str) -> bool:
        """Delete a secret"""
        return self.backend.delete_secret(name)
    
    def rotate(self, name: str, new_value: Dict) -> bool:
        """Rotate a secret (delete old, create new)"""
        logger.info(f"Rotating secret: {name}")
        return self.backend.put_secret(name, new_value)


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
@click.group()
def cli():
    """Secrets Manager CLI - Manage AWS Secrets Manager & HashiCorp Vault"""
    pass


@cli.command()
@click.option('--backend', type=click.Choice(['aws', 'vault']), default='aws')
@click.option('--region', default='us-east-1', help='AWS region (for AWS backend)')
@click.option('--vault-url', default='http://127.0.0.1:8200', help='Vault URL')
def list_secrets(backend, region, vault_url):
    """List all secrets"""
    kwargs = {'region': region} if backend == 'aws' else {'url': vault_url}
    manager = SecretsManager(backend=backend, **kwargs)
    
    secrets = manager.list()
    
    if not secrets:
        console.print("[yellow]No secrets found[/]")
        return
    
    table = Table(title=f"Secrets ({backend.upper()})", box=box.ROUNDED)
    table.add_column("Secret Name", style="cyan")
    
    for secret in secrets:
        table.add_row(secret)
    
    console.print(table)


@cli.command()
@click.argument('name')
@click.option('--backend', type=click.Choice(['aws', 'vault']), default='aws')
@click.option('--region', default='us-east-1')
@click.option('--vault-url', default='http://127.0.0.1:8200')
def get(name, backend, region, vault_url):
    """Retrieve a secret"""
    kwargs = {'region': region} if backend == 'aws' else {'url': vault_url}
    manager = SecretsManager(backend=backend, **kwargs)
    
    secret = manager.get(name)
    
    if secret:
        console.print(f"[green]Secret '{name}':[/]")
        console.print_json(data=secret)
    else:
        console.print(f"[red]Secret '{name}' not found[/]")


@cli.command()
@click.argument('name')
@click.option('--file', type=click.Path(exists=True), help='JSON file with secret data')
@click.option('--key', help='Single key to store')
@click.option('--value', help='Value for single key')
@click.option('--backend', type=click.Choice(['aws', 'vault']), default='aws')
@click.option('--region', default='us-east-1')
@click.option('--vault-url', default='http://127.0.0.1:8200')
def put(name, file, key, value, backend, region, vault_url):
    """Store a secret (from file or key-value pair)"""
    kwargs = {'region': region} if backend == 'aws' else {'url': vault_url}
    manager = SecretsManager(backend=backend, **kwargs)
    
    if file:
        with open(file) as f:
            secret_data = json.load(f)
    elif key and value:
        secret_data = {key: value}
    else:
        console.print("[red]Error: Provide either --file or both --key and --value[/]")
        sys.exit(1)
    
    if manager.put(name, secret_data):
        console.print(f"[green]✓[/] Secret '{name}' stored successfully")
    else:
        console.print(f"[red]✗[/] Failed to store secret '{name}'")
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--backend', type=click.Choice(['aws', 'vault']), default='aws')
@click.option('--region', default='us-east-1')
@click.option('--vault-url', default='http://127.0.0.1:8200')
@click.confirmation_option(prompt='Are you sure you want to delete this secret?')
def delete(name, backend, region, vault_url):
    """Delete a secret"""
    kwargs = {'region': region} if backend == 'aws' else {'url': vault_url}
    manager = SecretsManager(backend=backend, **kwargs)
    
    if manager.delete(name):
        console.print(f"[green]✓[/] Secret '{name}' deleted")
    else:
        console.print(f"[red]✗[/] Failed to delete secret '{name}'")
        sys.exit(1)


if __name__ == '__main__':
    cli()