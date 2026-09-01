# Computational requirements

## Public result reproduction

Python 3.11 with NumPy and pandas is sufficient for public/core validation. Matplotlib and Pillow are additionally required for the six public PNG/PDF figure sets. PyArrow is not required by the public/core route. The aggregate inputs are small; expected runtime is under a minute on a typical laptop. No network or model fitting is required.

## Full pipeline from authorized prepared inputs

Additional packages are PyArrow, LightGBM, xarray, netCDF4 and pyproj. Validate this tier with `workflows/validate_installation.py --full`. The audited correction run used:

- nested training: about 1,149 seconds;
- four-cell OOF assembly: about 111 seconds;
- downstream aggregate analysis: about 1 second;
- production fitting: about 45 seconds;
- new processed storage: about 157 MB.

These measurements are platform-specific. The public config defaults to one thread for portability; authorized users may set an explicit positive thread count and must record it. The full route does not generate a complete Alpine grid.
