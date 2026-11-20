import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'loan_offer_screen.dart';
import 'scaffold.dart';

class ReasonsScreen extends StatelessWidget {
  const ReasonsScreen({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final result = state.result!;
    final d = state.decision!;
    final reasons = (d['reasons'] as List).cast<Map<String, dynamic>>();
    final good = reasons.where((r) => r['kind'] == 'good');
    final bad = reasons.where((r) => r['kind'] == 'bad');
    final tips = (result['grounded_tips'] as List? ?? []).cast<Map<String, dynamic>>();
    final status = result['status'] as String;
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) => TLScaffold(
        state: state,
        title: state.t('why'),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (result['summary_bn'] != null)
              Card(
                color: TLColors.navy,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    result['summary_bn'] as String,
                    style: const TextStyle(color: Colors.white, fontSize: 16),
                  ),
                ),
              ),
            if (good.isNotEmpty) _Header(state.t('helped')),
            for (final r in good) _ReasonCard(reason: r, good: true, lang: state.lang),
            if (bad.isNotEmpty) _Header(state.t('improve')),
            for (final r in bad) _ReasonCard(reason: r, good: false, lang: state.lang),
            if (tips.isNotEmpty) _Header(state.t('tips')),
            for (final tip in tips)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.lightbulb_outline, color: TLColors.gold),
                  title: Text(tip['text'] as String),
                  subtitle: tip['source'] == null
                      ? null
                      : Text(
                          '${state.t('source')}: ${(tip['source'] as Map)['title']}',
                          style: const TextStyle(fontSize: 12),
                        ),
                ),
              ),
            if (status == 'needs_review') _Notice(state.t('review'), TLColors.gold),
            if (status == 'rejected' || status == 'blocked') _Notice(state.t('rejected'), TLColors.warn),
          ],
        ),
        bottom: status == 'approved'
            ? FilledButton(
                key: const Key('see_offer'),
                onPressed: () =>
                    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => LoanOfferScreen(state: state))),
                child: Text(state.t('see_offer')),
              )
            : OutlinedButton(
                onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
                child: Text(state.t('home')),
              ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 16, bottom: 4),
    child: Text(text, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
  );
}

class _ReasonCard extends StatelessWidget {
  const _ReasonCard({required this.reason, required this.good, required this.lang});

  final Map<String, dynamic> reason;
  final bool good;
  final String lang;

  @override
  Widget build(BuildContext context) => Card(
    key: Key('reason_${reason['feature']}'),
    color: (good ? TLColors.good : TLColors.warn).withValues(alpha: 0.08),
    child: ListTile(
      leading: Icon(
        good ? Icons.check_circle_rounded : Icons.warning_amber_rounded,
        color: good ? TLColors.good : TLColors.warn,
        size: 30,
      ),
      title: Text(
        lang == 'bn' ? reason['text'] as String : reason['label'] as String,
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      subtitle: Text(lang == 'bn' ? reason['label'] as String : reason['text'] as String),
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice(this.text, this.color);

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Card(
    color: color.withValues(alpha: 0.12),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Text(text, style: const TextStyle(fontSize: 16)),
    ),
  );
}
