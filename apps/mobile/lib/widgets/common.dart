import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../design/theme.dart';
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
      Icon(Icons.account_balance_wallet_rounded, size: size, color: TColor.tealDark, semanticLabel: 'wallet');
}

class LangToggle extends StatelessWidget {
  const LangToggle({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) => TextButton(
    key: const Key('lang_toggle'),
    onPressed: state.toggleLanguage,
    child: Text(
      state.lang == 'bn' ? 'English' : 'বাংলা',
      semanticsLabel: state.lang == 'bn' ? 'Switch to English' : 'বাংলায় দেখুন',
      style: const TextStyle(color: TColor.lightOnBrand),
    ),
  );
}

/// Section heading used in lists.
class SectionHeader extends StatelessWidget {
  const SectionHeader(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: TSpace.lg, bottom: TSpace.xs),
    child: Semantics(header: true, child: Text(text, style: Theme.of(context).textTheme.titleMedium)),
  );
}
