import 'package:flutter/material.dart';

import '../design/theme.dart';
import '../l10n.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import '../widgets/responsive.dart';
import 'scaffold.dart';

class RepaymentScreen extends StatefulWidget {
  const RepaymentScreen({super.key, required this.state});

  final AppState state;

  @override
  State<RepaymentScreen> createState() => _RepaymentScreenState();
}

class _RepaymentScreenState extends State<RepaymentScreen> {
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    if (widget.state.loan == null) widget.state.refreshLoan();
  }

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
    final isCompact = breakpointOf(context) == Breakpoint.compact;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) {
        final loan = s.loan ?? {};
        final onTime = (loan['on_time_repayments'] as int?) ?? 0;
        final limit = (loan['credit_limit_bdt'] as num?)?.toDouble() ?? s.amount;
        final upgraded = limit > s.amount + 1;
        final ladder = [s.amount, s.amount * 1.2, s.amount * 1.44];

        final limitCard = Card(
          child: Padding(
            padding: const EdgeInsets.all(TSpace.lg),
            child: Column(
              children: [
                Text(s.t('current_limit')),
                Text(
                  '৳ ${num2(limit, s.lang)}',
                  key: const Key('current_limit'),
                  style: const TextStyle(
                    fontSize: TType.headline - 2,
                    fontWeight: TFont.bold,
                    color: TColor.navy,
                  ),
                ),
                const SizedBox(height: TSpace.md),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    for (var i = 0; i < 3; i++)
                      Padding(
                        padding: const EdgeInsets.all(TSpace.xs + 2),
                        child: CircleAvatar(
                          radius: TSpace.lg + 2,
                          backgroundColor: i < onTime ? TColor.good : TColor.lightTrack,
                          child: Text(num2(i + 1, s.lang), style: const TextStyle(color: TColor.lightOnBrand)),
                        ),
                      ),
                  ],
                ),
                Text('${num2(onTime, s.lang)}/৩ ${s.t('paid_on_time')}', key: const Key('paid_count')),
              ],
            ),
          ),
        );

        final ladderList = [
          SectionHeader(s.t('limit_ladder')),
          Text(s.t('ladder_hint')),
          for (var i = 0; i < ladder.length; i++)
            ListTile(
              leading: Icon(
                limit >= ladder[i] - 1 ? Icons.check_circle : Icons.lock_outline,
                color: limit >= ladder[i] - 1 ? TColor.good : TColor.lightTextMuted,
              ),
              title: Text('৳ ${num2(ladder[i], s.lang)}'),
            ),
        ];

        final actionBtn = onTime >= 3 && !upgraded
            ? FilledButton(
                key: const Key('unlock_limit'),
                style: FilledButton.styleFrom(backgroundColor: TColor.gold, foregroundColor: TColor.navy),
                onPressed: _busy ? null : () => _do(() => s.api.upgradeLimit(s.applicationId!)),
                child: Text(s.t('unlock_limit')),
              )
            : null;

        final payBtn = onTime < 3
            ? FilledButton(
                key: const Key('pay_installment'),
                onPressed: _busy
                    ? null
                    : () => _do(() => s.api.repay(s.applicationId!, s.amount / 3, 'app-${onTime + 1}')),
                child: Text(s.t('pay_installment')),
              )
            : null;

        if (isCompact) {
          return TLScaffold(
            state: s,
            title: s.t('repay_title'),
            body: ListView(
              padding: const EdgeInsets.all(TSpace.lg),
              children: [
                limitCard,
                const SizedBox(height: TSpace.sm),
                ...ladderList,
                ?actionBtn,
              ],
            ),
            bottom: payBtn,
          );
        }

        return TLScaffold(
          state: s,
          title: s.t('repay_title'),
          body: Padding(
            padding: const EdgeInsets.all(TSpace.xl),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: Column(
                    children: [
                      limitCard,
                      const SizedBox(height: TSpace.lg),
                      ?payBtn,
                      ?actionBtn,
                    ],
                  ),
                ),
                const SizedBox(width: TSpace.lg),
                Expanded(
                  flex: 3,
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(TSpace.lg),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: ladderList,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
