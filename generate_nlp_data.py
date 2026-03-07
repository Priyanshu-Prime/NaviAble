import pandas as pd

# 0 = Fake/Accessibility Washed (Generic)
# 1 = Genuine/Spatially Specific (Detailed)
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
        "Lowered counters at the checkout register make it easy to pay from a seated position."
    ],
    "label": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
}

df = pd.DataFrame(data)
# Let's duplicate it a few times just to give the model enough rows to train on for this test
df = pd.concat([df]*20, ignore_index=True) 
df.to_csv("accessibility_reviews.csv", index=False)
print("Created accessibility_reviews.csv with 200 samples!")