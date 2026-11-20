import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../router.dart';
import '../state/app_state.dart';
import '../design/theme.dart';
import '../widgets/common.dart';
import '../widgets/responsive.dart';
import 'consent_screen.dart' show consentSources;

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.state});

  final AppState state;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _busy = false;

  Future<void> _toggle(String source, bool on) async {
    final s = widget.state;
    setState(() => _busy = true);
    try {
      if (on) {
        await s.api.grantConsent(s.userId!, source);
      } else {
        await s.api.revokeConsent(source);
      }
      await s.refreshProfile();
    } catch (e) {
      if (mounted) showError(context, s, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete() async {
    final s = widget.state;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(s.t('delete_confirm')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
          FilledButton(
            key: const Key('confirm_delete'),
            style: FilledButton.styleFrom(
              backgroundColor: TColor.bad,
              minimumSize: const Size(0, TLayout.buttonHeight - 8),
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(s.t('confirm')),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await s.deleteAll();
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      context.go(Routes.home);
      messenger.showSnackBar(SnackBar(content: Text(s.t('deleted'))));
    } catch (e) {
      if (mounted) showError(context, s, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    final isCompact = breakpointOf(context) == Breakpoint.compact;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) {
        final consentsList = [
          Text(
            s.t('active_consents'),
            style: const TextStyle(fontSize: TType.titleSmall, fontWeight: TFont.bold),
          ),
          for (final src in consentSources)
            SwitchListTile(
              key: Key('settings_consent_$src'),
              title: Text(s.t('src_$src')),
              value: s.consents.contains(src),
              onChanged: _busy || s.userId == null ? null : (on) => _toggle(src, on),
            ),
        ];

        final deleteBtn = OutlinedButton.icon(
          key: const Key('delete_data'),
          style: OutlinedButton.styleFrom(
            foregroundColor: TColor.bad,
            minimumSize: const Size.fromHeight(TLayout.buttonHeight),
          ),
          icon: const Icon(Icons.delete_forever),
          label: Text(s.t('delete_data')),
          onPressed: s.userId == null ? null : _delete,
        );

        return Scaffold(
          appBar: AppBar(
            title: Text(s.t('settings')),
            actions: [LangToggle(state: s)],
          ),
          body: isCompact
              ? ListView(
                  padding: const EdgeInsets.all(TSpace.lg),
                  children: [
                    ...consentsList,
                    const Divider(height: TSpace.xxl),
                    deleteBtn,
                  ],
                )
              : Padding(
                  padding: const EdgeInsets.all(TSpace.xl),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 3,
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(TSpace.lg),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: consentsList,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: TSpace.lg),
                      Expanded(
                        flex: 2,
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(TSpace.lg),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  s.t('delete_data'),
                                  style: const TextStyle(
                                    fontSize: TType.titleSmall,
                                    fontWeight: TFont.bold,
                                    color: TColor.bad,
                                  ),
                                ),
                                const SizedBox(height: TSpace.sm),
                                Text(
                                  s.t('delete_confirm'),
                                  style: const TextStyle(
                                    color: TColor.lightTextMuted,
                                    fontSize: TType.bodySmall,
                                  ),
                                ),
                                const SizedBox(height: TSpace.xl),
                                deleteBtn,
                              ],
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
