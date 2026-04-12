# Ramp Shapefile Tools

## Overlay preview

```zsh
cd /Users/vedantsunillande/spot-repo/NaviAble/NaviAble
source .venv/bin/activate
python yolo/ramp_shapefile_tools.py --mode overlay --shp /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/Ramps_v2/Sidewalk_Ramps_2010/Sidewalk_Ramps_2010.shp --out /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/ramp_exports/sidewalk_ramps_2010_overlay.png
```

## YOLO label export for a georeferenced raster tile

```zsh
cd /Users/vedantsunillande/spot-repo/NaviAble/NaviAble
source .venv/bin/activate
python yolo/ramp_shapefile_tools.py --mode labels --shp /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/Ramps_v2/Sidewalk_Ramps_2010/Sidewalk_Ramps_2010.shp --out-dir /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/ramp_exports --image-name tile_001.jpg --image-width 1024 --image-height 1024 --bounds XMIN YMIN XMAX YMAX
```

If you do not know the real image bounds yet, you can still use the overlay preview first.


