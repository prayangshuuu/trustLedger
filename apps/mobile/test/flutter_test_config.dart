import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

/// Golden comparison with a small tolerance, so anti-aliasing noise between machines does not
/// fail CI while real visual changes (layout, colour, text) still do. Goldens are generated on
/// macOS and CI runs the app job on macOS with the same pinned Flutter version.
const double goldenTolerance = 0.005; // 0.5% of pixels

class _TolerantComparator extends LocalFileComparator {
  _TolerantComparator(super.testFile);

  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async {
    final result = await GoldenFileComparator.compareLists(imageBytes, await getGoldenBytes(golden));
    if (result.passed || result.diffPercent <= goldenTolerance) {
      result.dispose();
      return true;
    }
    final error = await generateFailureOutput(result, golden, basedir);
    result.dispose();
    throw FlutterError(error);
  }
}

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  final current = goldenFileComparator;
  if (current is LocalFileComparator) {
    goldenFileComparator = _TolerantComparator(Uri.parse('${current.basedir}placeholder_test.dart'));
  }
  await testMain();
}
