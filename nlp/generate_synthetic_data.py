import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

import pandas as pd

data = {
    "text": [
        # FAKE / GENERIC REVIEWS (Label 0)
        "This place is great, fully accessible for everyone!",
        "Loved the food, wheelchairs can easily come inside.",
        "Very wheelchair friendly, 5 stars.",
        "Awesome mall, no problems for disabled people.",
        "Everything is accessible here, highly recommend.",
        # GENUINE / SPECIFIC REVIEWS (Label 1)
        "The side entrance has a smooth concrete ramp, but the main door has a 2-inch step.",
        "Grab bars are available in the ground floor restroom, door width is exactly 32 inches.",
        "Tactile paving leads directly from the sidewalk to the elevator bank.",
        "The ramp is a bit too steep at a 15-degree incline, manual wheelchairs might struggle.",
        "Lowered counters at the checkout register make it easy to pay from a seated position.",
    ],
    "label": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
}

df = pd.DataFrame(data)
df = pd.concat([df] * 20, ignore_index=True)

output_path = PROJECT_ROOT / "accessibility_reviews.csv"
df.to_csv(output_path, index=False)
print(f"Created {output_path} with {len(df)} samples!")
