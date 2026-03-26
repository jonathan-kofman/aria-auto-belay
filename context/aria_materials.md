# ARIA Materials

## Material Library (machine-readable)

| id              | name                | yield_mpa | ultimate_mpa | density_gcc | relative_cost | machinability | processes              |
|-----------------|---------------------|-----------|--------------|-------------|---------------|---------------|------------------------|
| 6061_t6         | 6061-T6 Aluminum    | 276       | 310          | 2.70        | 1.0           | 10            | cnc,dmls               |
| 7075_t6         | 7075-T6 Aluminum    | 503       | 572          | 2.81        | 2.5           | 7             | cnc                    |
| 4140_ht         | 4140 HT Steel       | 1000      | 1100         | 7.85        | 3.0           | 6             | cnc                    |
| 4340_steel      | 4340 Steel          | 1470      | 1720         | 7.85        | 4.0           | 5             | cnc                    |
| 17_4ph_h900     | 17-4PH H900         | 1310      | 1380         | 7.78        | 5.0           | 5             | cnc,dmls               |
| ti_6al_4v       | Ti-6Al-4V           | 880       | 950          | 4.43        | 12.0          | 3             | cnc,dmls               |
| 316l_ss         | 316L Stainless      | 290       | 580          | 8.00        | 3.5           | 6             | cnc,dmls               |
| 4140_normalized | 4140 Normalized     | 655       | 1020         | 7.85        | 2.5           | 7             | cnc                    |
| 6082_t6         | 6082-T6 Aluminum    | 260       | 310          | 2.71        | 1.2           | 9             | cnc                    |
| inconel_718     | Inconel 718         | 1100      | 1375         | 8.19        | 20.0          | 2             | cnc,dmls               |

> **Note:** The room-temp yield above (1100 MPa) differs from `cem_core.py` which uses 700 MPa — the elevated-temperature (700 degC) yield for hot-section analysis.

