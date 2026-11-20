import 'package:flutter/material.dart';

import 'screens/welcome_screen.dart';
import 'state/app_state.dart';
import 'theme.dart';

void main() => runApp(TrustLedgerApp(state: AppState()));

class TrustLedgerApp extends StatelessWidget {
  const TrustLedgerApp({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TrustLedger',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: WelcomeScreen(state: state),
    );
  }
}
