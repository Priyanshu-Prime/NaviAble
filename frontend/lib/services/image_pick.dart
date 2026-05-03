import 'dart:typed_data';

import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image_picker/image_picker.dart';
import 'package:native_exif/native_exif.dart';

class PickedPhoto {
  final Uint8List bytes;
  final String filename;
  final double? latitude;
  final double? longitude;
  const PickedPhoto({
    required this.bytes,
    required this.filename,
    this.latitude,
    this.longitude,
  });
}

class ImagePickService {
  final _picker = ImagePicker();

  Future<PickedPhoto?> pick({required ImageSource source}) async {
    final XFile? x = await _picker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 1920,
    );
    if (x == null) return null;

    double? lat, lon;
    try {
      final exif = await Exif.fromPath(x.path);
      final attrs = await exif.getLatLong();
      lat = attrs?.latitude;
      lon = attrs?.longitude;
      await exif.close();
    } catch (_) {/* not all platforms expose EXIF */}

    final bytes = await x.readAsBytes();
    final compressed = await FlutterImageCompress.compressWithList(
      bytes, quality: 85, minWidth: 1280, minHeight: 1280, format: CompressFormat.jpeg,
    );

    return PickedPhoto(
      bytes: compressed,
      filename: x.name,
      latitude: lat,
      longitude: lon,
    );
  }
}
