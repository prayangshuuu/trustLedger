import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trustledger_app/router.dart';
import 'package:trustledger_app/widgets/responsive.dart';

import 'helpers.dart';

void main() {
  test('protected routes redirect without a session or decision', () async {
    final anon = FakeBackend().state();
    for (final r in [Routes.consent, Routes.score, Routes.repay, Routes.settings]) {
      expect(redirectFor(anon, r), Routes.home);
    }
    expect(redirectFor(anon, Routes.home), isNull);

    final signed = await signedIn(FakeBackend());
    expect(redirectFor(signed, Routes.consent), isNull);
    expect(redirectFor(signed, Routes.score), Routes.connect);
    expect(redirectFor(signed, Routes.repay), Routes.connect);
    signed.result = moonResult();
    expect(redirectFor(signed, Routes.score), isNull);
    expect(redirectFor(signed, Routes.repay), isNull);
  });

  testWidgets('deep link without a session lands on welcome', (tester) async {
    await pumpApp(tester, FakeBackend().state(), '/reasons');
    expect(find.byKey(const Key('use_own_data')), findsOneWidget);
  });

  testWidgets('wide screens centre the phone layout on a backdrop', (tester) async {
    final state = await signedIn(FakeBackend(), withResult: true);
    await pumpApp(tester, state, '/score', size: const Size(1280, 800));
    final frame = tester.getSize(find.byType(Scaffold).last);
    expect(frame.width, lessThanOrEqualTo(520));
    expect(find.byType(ResponsiveFrame), findsWidgets);
  });
}
