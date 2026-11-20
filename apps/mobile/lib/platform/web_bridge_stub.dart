import 'dart:typed_data';

/// A file chosen or dropped in the browser.
class PickedFile {
  PickedFile(this.name, this.bytes);

  final String name;
  final Uint8List bytes;
}

/// Session values kept for the browser tab only (never sensitive data).
String? sessionGet(String key) => null;

void sessionSet(String key, String? value) {}

/// Opens the browser file picker (camera capture on phones when [camera] is true).
Future<PickedFile?> pickFile({required String accept, bool camera = false}) async => null;

/// Starts listening for files dropped anywhere on the page; returns a function that stops it.
void Function() listenForDrops(void Function(PickedFile file) onFile) => () {};
