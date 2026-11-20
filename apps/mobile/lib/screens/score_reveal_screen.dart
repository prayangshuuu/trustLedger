import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/score_meter.dart';
import 'scaffold.dart';

class ScoreRevealScreen extends StatelessWidget {
  const ScoreRevealScreen({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        final d = state.decision;
        if (d == null) return const SizedBox.shrink();
        final band = d['band'] as String;
        return TLScaffold(
          state: state,
          title: state.t('your_score'),
          body: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                KeyedSubtree(
                  key: const Key('band_chip'),
                  child: ScoreMeter(score: d['score'] as int, label: state.t('band_$band'), color: bandColor(band)),
                ),
                const SizedBox(height: TSpace.sm),
                const Text('300 — 900', style: TextStyle(color: TColor.lightTextMuted)),
              ],
            ),
          ),
          bottom: FilledButton(
            key: const Key('see_reasons'),
            onPressed: () => context.push(Routes.reasons),
            child: Text(state.t('why')),
          ),
        );
      },
    );
  }
}
