// Web-only capabilities behind one interface; mobile/desktop get the no-op implementation.
export 'web_bridge_stub.dart' if (dart.library.js_interop) 'web_bridge_web.dart';
