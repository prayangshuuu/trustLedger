import 'package:flutter/material.dart';

import '../l10n.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'repayment_screen.dart';
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
      await Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => RepaymentScreen(state: s)));
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
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('offer_title'),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const WalletIcon(size: 56),
            const SizedBox(height: 16),
            Text(s.t('offer_amount'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
            Text(
              '৳ ${num2(s.amount, s.lang)}',
              key: const Key('offer_amount'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w700, color: TLColors.navy),
            ),
            const SizedBox(height: 8),
            Text(
              '${s.t('installments')} · ৳ ${num2(s.amount / 3, s.lang)}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16),
            ),
          ],
        ),
        bottom: FilledButton(
          key: const Key('accept_offer'),
          onPressed: _busy ? null : _accept,
          child: _busy ? const CircularProgressIndicator(color: Colors.white) : Text(s.t('accept')),
        ),
      ),
    );
  }
}
