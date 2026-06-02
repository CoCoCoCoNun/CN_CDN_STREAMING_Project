#utils.py
def read_config(file_path: str) -> dict:
    config_data = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line:
                key, value = line.split('=')
                ip, port = value.split(':')
                config_data[key.strip()] = (ip.strip(), int(port.strip()))
    return config_data
