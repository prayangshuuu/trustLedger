import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

class PickedFile {
  PickedFile(this.name, this.bytes);

  final String name;
  final Uint8List bytes;
}

String? sessionGet(String key) {
  try {
    return web.window.sessionStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

void sessionSet(String key, String? value) {
  try {
    if (value == null) {
      web.window.sessionStorage.removeItem(key);
    } else {
      web.window.sessionStorage.setItem(key, value);
    }
  } catch (_) {
    // storage disabled (private mode): the session simply does not survive a reload
  }
}

Future<PickedFile?> _read(web.File file) async {
  final buffer = await file.arrayBuffer().toDart;
  return PickedFile(file.name, buffer.toDart.asUint8List());
}

Future<PickedFile?> pickFile({required String accept, bool camera = false}) {
  final completer = Completer<PickedFile?>();
  final input = web.HTMLInputElement()
    ..type = 'file'
    ..accept = accept;
  if (camera) input.setAttribute('capture', 'environment');
  input.onchange = ((web.Event _) {
    final files = input.files;
    if (files == null || files.length == 0) {
      completer.complete(null);
    } else {
      _read(files.item(0)!).then(completer.complete, onError: completer.completeError);
    }
  }).toJS;
  input.click();
  return completer.future;
}

void Function() listenForDrops(void Function(PickedFile file) onFile) {
  final over = ((web.DragEvent e) => e.preventDefault()).toJS;
  final drop = ((web.DragEvent e) {
    e.preventDefault();
    final files = e.dataTransfer?.files;
    if (files != null && files.length > 0) {
      _read(files.item(0)!).then((f) {
        if (f != null) onFile(f);
      });
    }
  }).toJS;
  web.document.addEventListener('dragover', over);
  web.document.addEventListener('drop', drop);
  return () {
    web.document.removeEventListener('dragover', over);
    web.document.removeEventListener('drop', drop);
  };
}
