# Validation Lessons

Common failures encountered during generation.


- **2x**: bbox: minimum axis 10.0mm is much larger than thickness=6.0mm. The base plate should be ~6.0mm thin.

- **1x**: bbox: minimum axis 9.0mm is much larger than thickness=6.0mm. The base plate should be ~6.0mm thin.

- **1x**: feature_complexity: goal specifies 4 holes but geometry has only 13 faces — holes may not be cut. Ne

- **1x**: feature_complexity: goal specifies 4 holes but geometry has only 4 faces — holes may not be cut. Nee

- **1x**: bbox: no axis matches OD=30.0mm (closest=41.7mm, tol=6.0). Check the code — a value in .extrude() or

- **1x**: bbox: no axis matches depth=3.0mm (closest=6.0mm, tol=2.0). Check the code — a value in .extrude() o