import os
import re
import sys

def get_required_keys(directory):
    """Greps the code for environment variable keys."""
    keys = set()
    # Patterns for os.getenv("KEY") and env_vars.get("KEY")
    patterns = [
        r'os\.getenv\(["\']([^"\']+)["\']\)',
        r'env_vars\.get\(["\']([^"\']+)["\']\)'
    ]
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        keys.update(matches)
    return keys

def get_env_keys(env_file):
    """Loads keys from the generated .env file."""
    keys = set()
    if not os.path.exists(env_file):
        return keys
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=')[0].strip()
                keys.add(key)
    return keys

def main():
    code_dir = 'invoice_cdk'
    env_file = '.env'
    
    print(f"--- Validating Environment Variables ---")
    
    required_keys = get_required_keys(code_dir)
    # Ignore internal AWS/CDK variables and derived variables
    # MONGODB_URI and DB_NAME are constructed in lambda_functions.py 
    # from MONGO_USER, MONGO_PW, etc.
    ignored_keys = {
        'CDK_DEFAULT_ACCOUNT', 
        'CDK_DEFAULT_REGION', 
        'MONGODB_URI', 
        'DB_NAME'
    }
    required_keys = required_keys - ignored_keys
    
    provided_keys = get_env_keys(env_file)
    
    missing_keys = required_keys - provided_keys
    
    if missing_keys:
        print(f"ERROR: The following environment variables are used in the code but MISSING in {env_file}:")
        for key in sorted(missing_keys):
            print(f"  - {key}")
        print("\nPlease add them to your GitHub Secrets (ENV_PROD_CONTENT or ENV_DEV_CONTENT).")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(required_keys)} variables found in the code are present in {env_file}.")

if __name__ == "__main__":
    main()
