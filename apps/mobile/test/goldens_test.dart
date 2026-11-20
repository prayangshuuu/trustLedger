import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trustledger_app/main.dart';
import 'package:trustledger_app/router.dart';
import 'package:trustledger_app/state/app_state.dart';

import 'helpers.dart';

Future<void> _loadTestFonts() async {
  final fontLoader = FontLoader('HindSiliguri');
  fontLoader.addFont(rootBundle.load('assets/fonts/HindSiliguri-Regular.ttf'));
  fontLoader.addFont(rootBundle.load('assets/fonts/HindSiliguri-Medium.ttf'));
  fontLoader.addFont(rootBundle.load('assets/fonts/HindSiliguri-SemiBold.ttf'));
  fontLoader.addFont(rootBundle.load('assets/fonts/HindSiliguri-Bold.ttf'));
  await fontLoader.load();
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    try {
      await _loadTestFonts();
    } catch (_) {}
  });

  const mobileSize = Size(390, 844);
  const desktopSize = Size(1280, 800);

  Future<void> pumpScreen(
    WidgetTester tester,
    AppState state,
    String route,
    Size size,
  ) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(TrustLedgerApp(state: state, initialLocation: route));
    await tester.pumpAndSettle();
  }

  testWidgets('welcome screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = backend.state();

    await pumpScreen(tester, state, Routes.home, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/welcome_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.home, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/welcome_desktop.png'),
    );
  });

  testWidgets('consent screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend);

    await pumpScreen(tester, state, Routes.consent, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/consent_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.consent, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/consent_desktop.png'),
    );
  });

  testWidgets('score reveal final frame goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend, withResult: true);

    await pumpScreen(tester, state, Routes.score, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/score_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.score, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/score_desktop.png'),
    );
  });

  testWidgets('reasons screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend, withResult: true);

    await pumpScreen(tester, state, Routes.reasons, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/reasons_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.reasons, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/reasons_desktop.png'),
    );
  });

  testWidgets('loan offer screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend, withResult: true);

    await pumpScreen(tester, state, Routes.loan, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/loan_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.loan, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/loan_desktop.png'),
    );
  });

  testWidgets('bhorsha chat screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend);

    await pumpScreen(tester, state, Routes.bhorsha, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/bhorsha_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.bhorsha, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/bhorsha_desktop.png'),
    );
  });

  testWidgets('settings screen goldens', (tester) async {
    final backend = FakeBackend();
    final state = await signedIn(backend);

    await pumpScreen(tester, state, Routes.settings, mobileSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/settings_mobile.png'),
    );

    await pumpScreen(tester, state, Routes.settings, desktopSize);
    await expectLater(
      find.byType(TrustLedgerApp),
      matchesGoldenFile('goldens/settings_desktop.png'),
    );
  });
}
