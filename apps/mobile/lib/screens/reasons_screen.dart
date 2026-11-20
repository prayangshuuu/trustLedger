import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class ReasonsScreen extends StatelessWidget {
  const ReasonsScreen({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        final result = state.result;
        final d = state.decision;
        if (result == null || d == null) return const SizedBox.shrink();
        final reasons = (d['reasons'] as List).cast<Map<String, dynamic>>();
        final good = reasons.where((r) => r['kind'] == 'good');
        final bad = reasons.where((r) => r['kind'] == 'bad');
        final tips = (result['grounded_tips'] as List? ?? []).cast<Map<String, dynamic>>();
        final status = result['status'] as String;
        return TLScaffold(
          state: state,
          title: state.t('why'),
          body: ListView(
            padding: const EdgeInsets.all(TSpace.lg),
            children: [
              if (result['summary_bn'] != null)
                Card(
                  color: TColor.navy,
                  child: Padding(
                    padding: const EdgeInsets.all(TSpace.lg),
                    child: Text(
                      result['summary_bn'] as String,
                      style: const TextStyle(color: TColor.lightOnBrand, fontSize: TType.body),
                    ),
                  ),
                ),
              if (good.isNotEmpty) SectionHeader(state.t('helped')),
              for (final r in good) _ReasonCard(reason: r, good: true, lang: state.lang),
              if (bad.isNotEmpty) SectionHeader(state.t('improve')),
              for (final r in bad) _ReasonCard(reason: r, good: false, lang: state.lang),
              if (tips.isNotEmpty) SectionHeader(state.t('tips')),
              for (final tip in tips)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.lightbulb_outline, color: TColor.gold),
                    title: Text(tip['text'] as String),
                    subtitle: tip['source'] == null
                        ? null
                        : Text(
                            '${state.t('source')}: ${(tip['source'] as Map)['title']}',
                            style: const TextStyle(fontSize: TType.caption),
                          ),
                  ),
                ),
              if (status == 'needs_review') _Notice(state.t('review'), TColor.gold),
              if (status == 'rejected' || status == 'blocked') _Notice(state.t('rejected'), TColor.warn),
            ],
          ),
          bottom: status == 'approved'
              ? FilledButton(
                  key: const Key('see_offer'),
                  onPressed: () => context.push(Routes.loan),
                  child: Text(state.t('see_offer')),
                )
              : OutlinedButton(onPressed: () => context.go(Routes.home), child: Text(state.t('home'))),
        );
      },
    );
  }
}

class _ReasonCard extends StatelessWidget {
  const _ReasonCard({required this.reason, required this.good, required this.lang});

  final Map<String, dynamic> reason;
  final bool good;
  final String lang;

  @override
  Widget build(BuildContext context) => Card(
    key: Key('reason_${reason['feature']}'),
    color: (good ? TColor.good : TColor.warn).withValues(alpha: 0.08),
    child: ListTile(
      leading: Icon(
        good ? Icons.check_circle_rounded : Icons.warning_amber_rounded,
        color: good ? TColor.good : TColor.warn,
        size: 30,
        semanticLabel: good ? 'helped' : 'to improve',
      ),
      title: Text(
        lang == 'bn' ? reason['text'] as String : reason['label'] as String,
        style: const TextStyle(fontWeight: TFont.semibold),
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
      padding: const EdgeInsets.all(TSpace.lg),
      child: Text(text, style: const TextStyle(fontSize: TType.body)),
    ),
  );
}
