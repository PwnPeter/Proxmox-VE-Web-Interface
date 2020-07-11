# Proxmox VE Web Interface

Upload a simple .csv (with columns `firstname, lastname, email`) file to clone VMs :)

## Get Started
```bash
pip3 -r requirements.txt
python3.8 main.py # python >= 3.0 required
```

## Mini Documentation

You can edit the dictionaries below :
```json
os_equivalent = {
    "1": "CentOS",
    "2": "Debian",
    "3": "Linux_Autre",
    "4": "WinXP",
    "5": "Win7",
    "6": "Win10",
    "7": "WinSRV2016",
    "8": "WinSRV2019",
    "9": "Win_Autre",
}

template_equivalent = {
    "CentOS": 100,
    "WinSRV2016": 104,
}

classe_equivalent = {
    "1": "ING1",
    "2": "ING2",
    "3": "IR3",
    "4": "IR4",
    "5": "IR5",
    "6": "Bachelor",
    "7": "M1",
    "8": "M2",
    "9": "Autre",
}
```

The value associated with one of the `os_equivalent' keys must match an equivalent `template_equivalent' key, ex:
```json
os_equivalent = {
    "1": "CentOS", # this value (CentOS) match with 
    "2": "Debian",
    "3": "Linux_Autre",
    "4": "WinXP",
    "5": "Win7",
    "6": "Win10",
    "7": "WinSRV2016",
    "8": "WinSRV2019",
    "9": "Win_Autre",
}

template_equivalent = {
    "CentOS": 100, # this template key (CentOS)
    "WinSRV2016": 104,
}
```