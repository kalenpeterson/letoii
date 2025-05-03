
from importlib import import_module

def get_vendor_modules():
    names=[
        'worldspice','spicehouse','burlapandbarrel','rumispice',
        'savoryspice','penzeys'
    ]
    modules={}
    for n in names:
        try:
            modules[n]=import_module(f'.{n}', package=__name__)
        except Exception as e:
            print(f'Failed to load {{n}}: {{e}}')
    return modules
