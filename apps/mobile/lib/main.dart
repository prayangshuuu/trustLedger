import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:go_router/go_router.dart';

import 'design/theme.dart';
import 'router.dart';
import 'state/app_state.dart';

Future<void> main() async {
  usePathUrlStrategy(); // real URLs on the web (/score, not /#/score)
  GoRouter.optionURLReflectsImperativeAPIs = true;
  WidgetsFlutterBinding.ensureInitialized();
  if (kIsWeb) SemanticsBinding.instance.ensureSemantics(); // screen readers + keyboard on the web
  final state = AppState();
  await state.restore();
  runApp(TrustLedgerApp(state: state));
}

class TrustLedgerApp extends StatefulWidget {
  const TrustLedgerApp({super.key, required this.state, this.initialLocation});

  final AppState state;
  final String? initialLocation;

  @override
  State<TrustLedgerApp> createState() => _TrustLedgerAppState();
}

class _TrustLedgerAppState extends State<TrustLedgerApp> {
  late final GoRouter _router = widget.initialLocation == null
      ? buildRouter(widget.state)
      : buildRouter(widget.state, initialLocation: widget.initialLocation!);

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'TrustLedger',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      routerConfig: _router,
    );
  }
}
