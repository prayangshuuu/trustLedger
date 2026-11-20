// End-to-end flows against a running local API (DEMO_MODE=true, seeded personas).
//   flutter test integration_test -d macos --dart-define=API_BASE_URL=http://127.0.0.1:8000
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:trustledger_app/main.dart';
import 'package:trustledger_app/state/app_state.dart';

Future<void> waitFor(WidgetTester tester, Finder finder, {int seconds = 30}) async {
  for (var i = 0; i < seconds * 10; i++) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isNotEmpty) return;
  }
  throw TestFailure('Timed out waiting for $finder');
}

Future<void> tapKey(WidgetTester tester, String key) async {
  // Routes below the top one stay built, so only consider widgets that can receive the tap
  final f = find.byKey(Key(key)).hitTestable().first;
  await waitFor(tester, find.byKey(Key(key)).hitTestable());
  await tester.ensureVisible(f);
  await tester.tap(f);
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Moon: consent, SMS + bill, score, reasons, loan, 3 repayments, limit +20%', (tester) async {
    final state = AppState();
    await state.api.resetDemo();
    await tester.pumpWidget(TrustLedgerApp(state: state));
    if (find.byKey(const Key('try_demo_switch')).evaluate().isNotEmpty) {
      await tapKey(tester, 'try_demo_switch');
    }
    await tapKey(tester, 'persona_moon');
    for (final src in ['sms', 'bills', 'recharge', 'ocr']) {
      await waitFor(tester, find.byKey(Key('consent_$src')));
      final tile = tester.widget<SwitchListTile>(find.byKey(Key('consent_$src')));
      if (!tile.value) await tapKey(tester, 'consent_$src');
    }
    await tapKey(tester, 'consent_continue');
    await tapKey(tester, 'import_sms');
    await tapKey(tester, 'upload_bill');
    await waitFor(tester, find.textContaining('DESCO'));
    await tapKey(tester, 'get_score');

    await waitFor(tester, find.byKey(const Key('band_chip')), seconds: 60);
    await tester.pumpAndSettle();
    expect(state.result!['status'], 'approved');
    final score = state.decision!['score'] as int;
    expect(score, greaterThanOrEqualTo(650));
    expect(find.text('$score'), findsOneWidget);

    await tapKey(tester, 'see_reasons');
    await waitFor(tester, find.byIcon(Icons.check_circle_rounded));
    await tapKey(tester, 'see_offer');
    await tapKey(tester, 'accept_offer');
    for (var i = 0; i < 3; i++) {
      await tapKey(tester, 'pay_installment');
      await tester.pump(const Duration(seconds: 1));
    }
    await tapKey(tester, 'unlock_limit');
    await tester.pump(const Duration(seconds: 1));
    expect(state.loan!['credit_limit_bdt'], closeTo(18000, 1));
  });

  testWidgets('Newcomer: zero history -> Bhorsha chat -> score; then delete my data', (tester) async {
    final state = AppState();
    await state.api.resetDemo();
    await tester.pumpWidget(TrustLedgerApp(state: state));
    await tapKey(tester, 'persona_newcomer');
    await tapKey(tester, 'consent_bhorsha');
    await tapKey(tester, 'consent_continue');

    await waitFor(tester, find.byKey(const Key('bhorsha_input')), seconds: 60);
    const answers = [
      'মাসের শুরুতে বাজেট করি, বাসাভাড়া আর বিল আগে আলাদা রাখি',
      'প্রতি মাসে অল্প করে সঞ্চয় করি, ডিপিএস আছে',
      'এমন লোভনীয় প্রস্তাবে না করে দেব, এটা ঝুঁকি',
      'জরুরি অবস্থার জন্য কিছু টাকা আলাদা রাখি',
      'প্রতি মাসে নিয়মিত একই পরিকল্পনা মেনে চলি',
      'কিস্তি সময়মতো শোধ করি, ঋণ শোধ আমার দায়িত্ব',
      'তালিকা করে খরচ করি যাতে মাসের শেষে টান না পড়ে',
      'আয় কম হলেও কিছু সঞ্চয় রাখার চেষ্টা করি',
      'অচেনা কারো কথায় বিনিয়োগ করি না, আগে যাচাই করি',
      'হাসপাতালের খরচের জন্য ইমার্জেন্সি টাকা রাখি',
      'প্রতি সপ্তাহে একই দিনে হিসাব মিলিয়ে দেখি',
      'ভুল হলে সত্যি কথা বলি এবং টাকা ফেরত দিই',
    ];
    bool sendEnabled() {
      final btn = find.byKey(const Key('bhorsha_send'));
      return btn.evaluate().isNotEmpty && tester.widget<IconButton>(btn).onPressed != null;
    }

    for (final a in answers) {
      // Wait for the previous reply (send button re-enabled) or the end of the interview
      for (var i = 0; i < 300 && !sendEnabled(); i++) {
        if (find.byKey(const Key('bhorsha_finish')).evaluate().isNotEmpty) break;
        await tester.pump(const Duration(milliseconds: 100));
      }
      if (find.byKey(const Key('bhorsha_finish')).evaluate().isNotEmpty) break;
      await Future<void>.delayed(const Duration(seconds: 2)); // real reading time
      tester.widget<TextField>(find.byKey(const Key('bhorsha_input'))).controller!.text = a;
      await tester.pump();
      await tester.tap(find.byKey(const Key('bhorsha_send')));
      await tester.pump(const Duration(milliseconds: 200));
    }
    await tapKey(tester, 'bhorsha_finish');
    await waitFor(tester, find.byKey(const Key('band_chip')), seconds: 60);
    expect(state.decision!['reasons'], isNotEmpty);

    await tapKey(tester, 'open_settings');
    await tapKey(tester, 'delete_data');
    await tapKey(tester, 'confirm_delete');
    await tester.pump(const Duration(seconds: 2));
    expect(state.userId, isNull);
    expect(find.byKey(const Key('persona_moon')), findsOneWidget);
  });
}
