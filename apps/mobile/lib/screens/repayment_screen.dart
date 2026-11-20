import 'package:flutter/material.dart';

import '../l10n.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class RepaymentScreen extends StatefulWidget {
  const RepaymentScreen({super.key, required this.state});

  final AppState state;

  @override
  State<RepaymentScreen> createState() => _RepaymentScreenState();
}

class _RepaymentScreenState extends State<RepaymentScreen> {
  bool _busy = false;

  Future<void> _do(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      await widget.state.refreshLoan();
    } catch (e) {
      if (mounted) showError(context, widget.state, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    final loan = s.loan ?? {};
    final onTime = (loan['on_time_repayments'] as int?) ?? 0;
    final limit = (loan['credit_limit_bdt'] as num?)?.toDouble() ?? s.amount;
    final upgraded = limit > s.amount + 1;
    final ladder = [s.amount, s.amount * 1.2, s.amount * 1.44];
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('repay_title'),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(s.t('current_limit')),
                    Text(
                      '৳ ${num2(limit, s.lang)}',
                      key: const Key('current_limit'),
                      style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: TLColors.navy),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        for (var i = 0; i < 3; i++)
                          Padding(
                            padding: const EdgeInsets.all(6),
                            child: CircleAvatar(
                              radius: 18,
                              backgroundColor: i < onTime ? TLColors.good : Colors.black12,
                              child: Text(num2(i + 1, s.lang), style: const TextStyle(color: Colors.white)),
                            ),
                          ),
                      ],
                    ),
                    Text('${num2(onTime, s.lang)}/৩ ${s.t('paid_on_time')}', key: const Key('paid_count')),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(s.t('limit_ladder'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            Text(s.t('ladder_hint')),
            for (var i = 0; i < ladder.length; i++)
              ListTile(
                leading: Icon(
                  limit >= ladder[i] - 1 ? Icons.check_circle : Icons.lock_outline,
                  color: limit >= ladder[i] - 1 ? TLColors.good : Colors.black38,
                ),
                title: Text('৳ ${num2(ladder[i], s.lang)}'),
              ),
            if (onTime >= 3 && !upgraded)
              FilledButton(
                key: const Key('unlock_limit'),
                style: FilledButton.styleFrom(backgroundColor: TLColors.gold),
                onPressed: _busy ? null : () => _do(() => s.api.upgradeLimit(s.applicationId!)),
                child: Text(s.t('unlock_limit')),
              ),
          ],
        ),
        bottom: onTime < 3
            ? FilledButton(
                key: const Key('pay_installment'),
                onPressed: _busy
                    ? null
                    : () => _do(() => s.api.repay(s.applicationId!, s.amount / 3, 'app-${onTime + 1}')),
                child: Text(s.t('pay_installment')),
              )
            : null,
      ),
    );
  }
}
