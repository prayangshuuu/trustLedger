import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../state/app_state.dart';

/// Show a Bangla-friendly error with an optional retry action.
void showError(BuildContext context, AppState state, Object error, {VoidCallback? onRetry}) {
  final key = error is ApiException ? error.l10nKey : 'err_generic';
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(state.t(key)),
      duration: const Duration(seconds: 5),
      action: onRetry == null ? null : SnackBarAction(label: state.t('retry'), onPressed: onRetry),
    ),
  );
}

/// Generic wallet glyph (no bank or MFS logos).
class WalletIcon extends StatelessWidget {
  const WalletIcon({super.key, this.size = 28});

  final double size;

  @override
  Widget build(BuildContext context) =>
      Icon(Icons.account_balance_wallet_rounded, size: size, color: Theme.of(context).colorScheme.primary);
}

class LangToggle extends StatelessWidget {
  const LangToggle({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) => TextButton(
    key: const Key('lang_toggle'),
    onPressed: state.toggleLanguage,
    child: Text(state.lang == 'bn' ? 'English' : 'বাংলা', style: const TextStyle(color: Colors.white)),
  );
}
