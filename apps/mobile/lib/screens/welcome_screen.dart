import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key, required this.state});

  final AppState state;

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  late Future<List<dynamic>> _personas;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _personas = widget.state.api.personas();
  }

  Future<void> _pick(Map<String, dynamic> persona) async {
    setState(() => _busy = true);
    try {
      await widget.state.selectPersona(persona);
      if (!mounted) return;
      context.push(Routes.consent);
    } catch (e) {
      if (mounted) showError(context, widget.state, e, onRetry: () => _pick(persona));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) => Scaffold(
        backgroundColor: TColor.navy,
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(TSpace.xl),
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: LangToggle(state: s),
              ),
              const SizedBox(height: TSpace.xl),
              const Icon(Icons.verified_user_rounded, color: TColor.teal, size: 64, semanticLabel: 'TrustLedger'),
              const SizedBox(height: TSpace.md),
              Semantics(
                header: true,
                child: Text(
                  s.t('app_name'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: TColor.lightOnBrand, fontSize: TType.headline, fontWeight: TFont.bold),
                ),
              ),
              const SizedBox(height: TSpace.sm),
              Text(
                s.t('tagline'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: TColor.lightOnBrandMuted, fontSize: TType.body),
              ),
              const SizedBox(height: TSpace.xxl),
              Text(
                s.t('demo_mode'),
                style: const TextStyle(color: TColor.gold, fontWeight: TFont.semibold),
              ),
              const SizedBox(height: TSpace.sm),
              FutureBuilder<List<dynamic>>(
                future: _personas,
                builder: (context, snap) {
                  if (snap.hasError) {
                    return Column(
                      children: [
                        Text(s.t('err_network'), style: const TextStyle(color: TColor.lightOnBrand)),
                        TextButton(
                          onPressed: () => setState(() => _personas = s.api.personas()),
                          child: Text(s.t('retry')),
                        ),
                      ],
                    );
                  }
                  if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                  return Column(
                    children: [
                      for (final p in snap.data!.cast<Map<String, dynamic>>())
                        Card(
                          child: ListTile(
                            key: Key('persona_${p['key']}'),
                            leading: const WalletIcon(),
                            title: Text(
                              _personaName(p['key'] as String, s.lang),
                              style: const TextStyle(fontWeight: TFont.semibold),
                            ),
                            subtitle: Text(p['description'] as String),
                            trailing: _busy ? null : const Icon(Icons.arrow_forward),
                            onTap: _busy ? null : () => _pick(p),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _personaName(String key, String lang) => switch ((key, lang)) {
  ('moon', 'bn') => 'মুন — পোশাক শ্রমিক',
  ('student', 'bn') => 'রাফি — ছাত্র ও ফ্রিল্যান্সার',
  ('homemaker', 'bn') => 'রিনা — গৃহিণী (ভরসা সম্পন্ন)',
  ('newcomer', 'bn') => 'মিতু — নতুন (কোনো ইতিহাস নেই)',
  ('moon', _) => 'Moon — garment worker',
  ('student', _) => 'Rafi — student and freelancer',
  ('homemaker', _) => 'Rina — homemaker (Bhorsha done)',
  _ => 'Mitu — newcomer (no history)',
};
