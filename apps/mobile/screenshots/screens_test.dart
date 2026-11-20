// Renders key screens to PNG for docs/media (not part of the normal test run):
//   flutter test screenshots --update-goldens
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trustledger_app/screens/consent_screen.dart';
import 'package:trustledger_app/screens/reasons_screen.dart';
import 'package:trustledger_app/screens/score_reveal_screen.dart';
import 'package:trustledger_app/theme.dart';

import '../test/helpers.dart';

Future<void> loadFonts() async {
  final loader = FontLoader('HindSiliguri');
  for (final w in ['Regular', 'Medium', 'SemiBold', 'Bold']) {
    loader.addFont(rootBundle.load('assets/fonts/HindSiliguri-$w.ttf'));
  }
  await loader.load();
  final icons = FontLoader('MaterialIcons')..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
  await icons.load();
}

Future<void> shot(WidgetTester tester, Widget screen, String name) async {
  tester.view.physicalSize = const Size(1080, 2160);
  tester.view.devicePixelRatio = 2.75;
  await tester.pumpWidget(MaterialApp(debugShowCheckedModeBanner: false, theme: buildTheme(), home: screen));
  await tester.pumpAndSettle();
  await expectLater(find.byType(MaterialApp), matchesGoldenFile('../../../docs/media/app_$name.png'));
}

void main() {
  setUpAll(loadFonts);

  testWidgets('consent', (tester) async {
    final backend = FakeBackend()..consents.addAll({'sms', 'bills', 'ocr'});
    final state = backend.state();
    await tester.runAsync(() => state.selectPersona({'user_id': 'u1', 'key': 'shathi', 'group': 'F_urban'}));
    await shot(tester, ConsentScreen(state: state), 'consent');
  });

  testWidgets('score', (tester) async {
    await shot(tester, ScoreRevealScreen(state: FakeBackend().state()..result = shathiResult()), 'score');
  });

  testWidgets('reasons', (tester) async {
    await shot(tester, ReasonsScreen(state: FakeBackend().state()..result = shathiResult()), 'reasons');
  });
}
