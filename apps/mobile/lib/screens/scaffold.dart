import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';

/// Shared page frame: title, language toggle and settings.
class TLScaffold extends StatelessWidget {
  const TLScaffold({super.key, required this.state, required this.title, required this.body, this.bottom});

  final AppState state;
  final String title;
  final Widget body;
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Semantics(header: true, child: Text(title)),
        actions: [
          LangToggle(state: state),
          if (state.userId != null)
            IconButton(
              key: const Key('open_settings'),
              icon: const Icon(Icons.settings),
              tooltip: state.t('settings'),
              onPressed: () => context.push(Routes.settings),
            ),
        ],
      ),
      body: SafeArea(child: body),
      bottomNavigationBar: bottom == null
          ? null
          : SafeArea(
              child: Padding(padding: const EdgeInsets.all(TSpace.lg), child: bottom),
            ),
    );
  }
}
