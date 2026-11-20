import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../l10n.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class LoanOfferScreen extends StatefulWidget {
  const LoanOfferScreen({super.key, required this.state});

  final AppState state;

  @override
  State<LoanOfferScreen> createState() => _LoanOfferScreenState();
}

class _LoanOfferScreenState extends State<LoanOfferScreen> {
  bool _busy = false;

  Future<void> _accept() async {
    final s = widget.state;
    setState(() => _busy = true);
    try {
      await s.api.disburse(s.applicationId!);
      await s.refreshLoan();
      if (!mounted) return;
      context.pushReplacement(Routes.repay);
    } catch (e) {
      if (mounted) showError(context, s, e, onRetry: _accept);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('offer_title'),
        body: ListView(
          padding: const EdgeInsets.all(TSpace.xl),
          children: [
            const WalletIcon(size: 56),
            const SizedBox(height: TSpace.lg),
            Text(
              s.t('offer_amount'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: TType.body),
            ),
            Text(
              '৳ ${num2(s.amount, s.lang)}',
              key: const Key('offer_amount'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: TType.headline + 6, fontWeight: TFont.bold, color: TColor.navy),
            ),
            const SizedBox(height: TSpace.sm),
            Text(
              '${s.t('installments')} · ৳ ${num2(s.amount / 3, s.lang)}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: TType.body),
            ),
          ],
        ),
        bottom: FilledButton(
          key: const Key('accept_offer'),
          onPressed: _busy ? null : _accept,
          child: _busy ? const CircularProgressIndicator(color: TColor.lightOnBrand) : Text(s.t('accept')),
        ),
      ),
    );
  }
}
