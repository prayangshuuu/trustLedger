import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trustledger_app/screens/reasons_screen.dart';
import 'package:trustledger_app/widgets/score_meter.dart';

import 'helpers.dart';

void main() {
  testWidgets('score meter animates from 300 up to the score', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: ScoreMeter(score: 691, label: 'ভালো')),
      ),
    );
    expect(find.text('300'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 900));
    final mid = int.parse(tester.widget<Text>(find.byKey(const Key('score_value'))).data!);
    expect(mid, inInclusiveRange(301, 690));
    await tester.pumpAndSettle();
    expect(find.text('691'), findsOneWidget);
    expect(find.text('ভালো'), findsOneWidget);
  });

  testWidgets('reduced motion shows the final score immediately', (tester) async {
    await tester.pumpWidget(
      const MediaQuery(
        data: MediaQueryData(disableAnimations: true),
        child: MaterialApp(
          home: Scaffold(body: ScoreMeter(score: 691, label: 'ভালো')),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('691'), findsOneWidget);
  });

  testWidgets('score reveal shows band in Bangla and opens Bangla reasons', (tester) async {
    final state = await signedIn(FakeBackend(), withResult: true);
    await pumpApp(tester, state, '/score');
    expect(find.text('691'), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('band_chip')), matching: find.text('ভালো')), findsOneWidget);

    await tester.tap(find.byKey(const Key('see_reasons')));
    await tester.pumpAndSettle();
    expect(find.byType(ReasonsScreen), findsOneWidget);
    expect(find.text('বিল সময়মতো পরিশোধ'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
    expect(find.textContaining('সূত্র'), findsOneWidget);
    expect(find.byKey(const Key('see_offer')), findsOneWidget);
  });

  testWidgets('language toggle switches to English labels', (tester) async {
    final state = await signedIn(FakeBackend(), withResult: true);
    await pumpApp(tester, state, '/score');
    await tester.tap(find.byKey(const Key('lang_toggle')));
    await tester.pumpAndSettle();
    expect(find.text('Your TrustLedger score'), findsOneWidget);
  });
}
