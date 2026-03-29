"""Quick diagnostic to check what fields are in the radar files."""
import pyart
from pathlib import Path

data_dir = Path('data/null')
for station_dir in data_dir.iterdir():
    if station_dir.is_dir():
        for f in station_dir.iterdir():
            if 'V06' in f.name:
                print(f'Loading: {f}')
                radar = pyart.io.read(str(f))
                print(f'Number of sweeps: {radar.nsweeps}')
                print(f'Available fields: {list(radar.fields.keys())}')

                for field_name in radar.fields:
                    data = radar.fields[field_name]['data']
                    print(f'  {field_name}: shape={data.shape}, min={data.min():.2f}, max={data.max():.2f}')
                break
        break
