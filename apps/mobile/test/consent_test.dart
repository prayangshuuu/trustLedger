import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trustledger_app/screens/consent_screen.dart';
import 'package:trustledger_app/screens/settings_screen.dart';
import 'package:trustledger_app/theme.dart';

import 'helpers.dart';

void main() {
  testWidgets('consent screen grants only the selected sources', (tester) async {
    final backend = FakeBackend();
    final state = backend.state();
    await state.selectPersona({'user_id': 'u1', 'key': 'shathi', 'group': 'F_urban'});
    await tester.pumpWidget(
      MaterialApp(
        theme: buildTheme(),
        home: ConsentScreen(state: state),
      ),
    );

    expect(find.text('লেনদেনের এসএমএস'), findsOneWidget);
    final continueBtn = find.byKey(const Key('consent_continue'));
    expect(tester.widget<FilledButton>(continueBtn).onPressed, isNull); // nothing selected yet

    await tester.tap(find.byKey(const Key('consent_sms')));
    await tester.tap(find.byKey(const Key('consent_bills')));
    await tester.pump();
    await tester.tap(continueBtn);
    await tester.pumpAndSettle();

    expect(backend.consents, {'sms', 'bills'});
    final grants = backend.requests.where((r) => r.url.path == '/consent');
    expect(grants.length, 2);
    expect(grants.first.headers['Authorization'], startsWith('Bearer tl1.'));
  });

  testWidgets('settings revokes consent and deletes data', (tester) async {
    final backend = FakeBackend()..consents.addAll({'sms', 'bhorsha'});
    final state = backend.state();
    await state.selectPersona({'user_id': 'u1', 'key': 'shathi', 'group': 'F_urban'});
    await tester.pumpWidget(
      MaterialApp(
        theme: buildTheme(),
        home: SettingsScreen(state: state),
      ),
    );

    await tester.tap(find.byKey(const Key('settings_consent_sms')));
    await tester.pumpAndSettle();
    expect(backend.consents, {'bhorsha'});

    await tester.tap(find.byKey(const Key('delete_data')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('confirm_delete')));
    await tester.pumpAndSettle();
    expect(backend.requests.any((r) => r.method == 'DELETE' && r.url.path == '/me'), isTrue);
    expect(state.userId, isNull);
  });
}
