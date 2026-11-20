import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../l10n.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class ReviewScreen extends StatefulWidget {
  const ReviewScreen({super.key, required this.state});

  final AppState state;

  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen> {
  bool _busy = false;

  AppState get s => widget.state;

  Future<void> _confirm() async {
    setState(() => _busy = true);
    try {
      final res = await s.confirmAndExtract();
      if (!mounted) return;
      if (res['needs_bhorsha'] == true) {
        context.pushReplacement(Routes.bhorsha);
      } else {
        context.pushReplacement(Routes.processing);
      }
    } catch (e) {
      if (mounted) showError(context, s, e, onRetry: _confirm);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _editTransaction(int index) {
    final tx = s.extractedTransactions[index];
    final amtCtrl = TextEditingController(text: tx['amount_bdt']?.toString() ?? '0');
    final counterCtrl = TextEditingController(text: tx['counterparty']?.toString() ?? '');
    String selectedType = tx['type']?.toString() ?? 'other';

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            left: TSpace.lg,
            right: TSpace.lg,
            top: TSpace.lg,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + TSpace.lg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                s.t('edit'),
                style: const TextStyle(fontSize: TType.headline, fontWeight: TFont.bold),
              ),
              const SizedBox(height: TSpace.md),
              TextField(
                controller: amtCtrl,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(
                  labelText: s.t('amount'),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: TSpace.sm),
              DropdownButtonFormField<String>(
                initialValue: selectedType,
                decoration: InputDecoration(
                  labelText: s.t('type'),
                  border: const OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'income', child: Text('আয় (Income)')),
                  DropdownMenuItem(value: 'bill', child: Text('বিল (Bill)')),
                  DropdownMenuItem(value: 'recharge', child: Text('রিচার্জ (Recharge)')),
                  DropdownMenuItem(value: 'transfer', child: Text('লেনদেন (Transfer)')),
                  DropdownMenuItem(value: 'savings', child: Text('সঞ্চয় (Savings)')),
                  DropdownMenuItem(value: 'other', child: Text('অন্যান্য (Other)')),
                ],
                onChanged: (val) {
                  if (val != null) setModalState(() => selectedType = val);
                },
              ),
              const SizedBox(height: TSpace.sm),
              TextField(
                controller: counterCtrl,
                decoration: InputDecoration(
                  labelText: s.t('provider'),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: TSpace.md),
              FilledButton(
                onPressed: () {
                  final newAmt = double.tryParse(amtCtrl.text) ?? (tx['amount_bdt'] as num).toDouble();
                  setState(() {
                    tx['amount_bdt'] = newAmt;
                    tx['type'] = selectedType;
                    tx['counterparty'] = counterCtrl.text.trim();
                    tx['confidence'] = 1.0; // User confirmed
                  });
                  Navigator.pop(ctx);
                },
                child: Text(s.t('save')),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _deleteTransaction(int index) {
    setState(() {
      s.extractedTransactions.removeAt(index);
    });
  }

  void _deleteBill(int index) {
    setState(() {
      s.extractedBills.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    final txs = s.extractedTransactions;
    final bills = s.extractedBills;

    return TLScaffold(
      state: s,
      title: s.t('review_title'),
      body: ListView(
        padding: const EdgeInsets.all(TSpace.lg),
        children: [
          Text(
            s.t('review_intro'),
            style: const TextStyle(color: TColor.lightTextMuted, fontSize: TType.body),
          ),
          const SizedBox(height: TSpace.md),
          if (bills.isNotEmpty) ...[
            Text(
              '${s.t('src_bills')} (${num2(bills.length, s.lang)})',
              style: const TextStyle(fontWeight: TFont.bold, fontSize: TType.titleSmall),
            ),
            const SizedBox(height: TSpace.xs),
            for (var i = 0; i < bills.length; i++)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.receipt_long, color: TColor.teal),
                  title: Text(
                    '${bills[i]['provider'] ?? bills[i]['merchant_or_platform'] ?? 'Utility'} · ৳${num2(bills[i]['amount_bdt'] ?? 0, s.lang)}',
                    style: const TextStyle(fontWeight: TFont.semibold),
                  ),
                  subtitle: Text(
                    '${bills[i]['due_date'] ?? bills[i]['bill_month'] ?? ''}',
                    style: const TextStyle(fontSize: TType.bodySmall),
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline, color: TColor.bad),
                    onPressed: () => _deleteBill(i),
                  ),
                ),
              ),
            const SizedBox(height: TSpace.md),
          ],
          Text(
            '${s.t('src_sms')} (${num2(txs.length, s.lang)})',
            style: const TextStyle(fontWeight: TFont.bold, fontSize: TType.titleSmall),
          ),
          const SizedBox(height: TSpace.xs),
          if (txs.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(TSpace.md),
                child: Text(
                  s.t('sms_loaded'),
                  style: const TextStyle(color: TColor.lightTextMuted),
                ),
              ),
            )
          else
            for (var i = 0; i < txs.length; i++) ...[
              Card(
                margin: const EdgeInsets.only(bottom: TSpace.xs),
                child: ListTile(
                  key: Key('tx_item_$i'),
                  leading: Icon(
                    txs[i]['direction'] == 'in' ? Icons.arrow_downward : Icons.arrow_upward,
                    color: txs[i]['direction'] == 'in' ? TColor.good : TColor.navy,
                    size: 20,
                  ),
                  title: Row(
                    children: [
                      Text(
                        '৳${num2(txs[i]['amount_bdt'] ?? 0, s.lang)}',
                        style: const TextStyle(fontWeight: TFont.bold),
                      ),
                      const SizedBox(width: TSpace.xs),
                      Text(
                        '(${txs[i]['type'] ?? ''})',
                        style: const TextStyle(fontSize: TType.bodySmall, color: TColor.lightTextMuted),
                      ),
                      const Spacer(),
                      if ((txs[i]['confidence'] as num? ?? 1.0) < 0.70)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: TColor.gold.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            s.t('low_confidence'),
                            style: const TextStyle(
                              color: TColor.warn,
                              fontSize: 11,
                              fontWeight: TFont.semibold,
                            ),
                          ),
                        ),
                    ],
                  ),
                  subtitle: Text(
                    '${txs[i]['counterparty'] ?? txs[i]['txn_id'] ?? ''}',
                    style: const TextStyle(fontSize: TType.bodySmall),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, size: 20),
                        onPressed: () => _editTransaction(i),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, size: 20, color: TColor.bad),
                        onPressed: () => _deleteTransaction(i),
                      ),
                    ],
                  ),
                ),
              ),
            ],
        ],
      ),
      bottom: FilledButton(
        key: const Key('confirm_review'),
        onPressed: _busy ? null : _confirm,
        child: _busy
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : Text(s.t('confirm_data')),
      ),
    );
  }
}
