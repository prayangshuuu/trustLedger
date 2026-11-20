import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../l10n.dart';
import '../platform/web_bridge.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class ConnectDataScreen extends StatefulWidget {
  const ConnectDataScreen({super.key, required this.state});

  final AppState state;

  @override
  State<ConnectDataScreen> createState() => _ConnectDataScreenState();
}

class _ConnectDataScreenState extends State<ConnectDataScreen> {
  bool _uploading = false;
  final _paste = TextEditingController();
  void Function()? _stopDrops;

  AppState get s => widget.state;

  @override
  void initState() {
    super.initState();
    // Web: a bill photo can be dropped anywhere on the page
    if (kIsWeb) _stopDrops = listenForDrops((f) => _upload(f.bytes, f.name, detect: true));
  }

  @override
  void dispose() {
    _stopDrops?.call();
    _paste.dispose();
    super.dispose();
  }

  Future<void> _importSampleSms() async {
    // Demo: synthetic SMS bundled with the app. The phone app reads SMS on the device.
    final raw = await rootBundle.loadString('assets/demo/moon_sms.json');
    final data = jsonDecode(raw) as Map<String, dynamic>;
    setState(() => s.sms = (data['sms'] as List).cast<String>());
  }

  void _usePasted(String text) async {
    final lines = text.split(RegExp(r'\r?\n')).map((l) => l.trim()).where((l) => l.isNotEmpty).toList();
    setState(() => s.sms = lines);
    if (s.personaKey == 'real_user') {
      try {
        final res = await s.api.uploadSms(s.userId!, rawText: text);
        setState(() {
          s.extractedTransactions = (res['transactions'] as List).cast<Map<String, dynamic>>();
        });
      } catch (e) {
        if (mounted) showError(context, s, e);
      }
    }
  }

  Future<void> _pickSmsFile() async {
    final f = await pickFile(accept: '.txt,.csv,.xml,text/plain,text/csv,text/xml');
    if (f != null) {
      if (s.personaKey == 'real_user') {
        try {
          final res = await s.api.uploadSms(s.userId!, bytes: f.bytes, filename: f.name);
          setState(() {
            s.extractedTransactions = (res['transactions'] as List).cast<Map<String, dynamic>>();
            s.sms = s.extractedTransactions.map((t) => t.toString()).toList();
          });
        } catch (e) {
          if (mounted) showError(context, s, e);
        }
      } else {
        _usePasted(utf8.decode(f.bytes, allowMalformed: true));
      }
    }
  }

  Future<void> _uploadSample() async {
    final bytes = await rootBundle.load('assets/demo/desco_bill.jpg');
    await _upload(bytes.buffer.asUint8List(), 'desco_bill.jpg');
  }

  Future<void> _pickPhoto({required bool camera}) async {
    final f = await pickFile(accept: 'image/jpeg,image/png,image/webp,application/pdf', camera: camera);
    if (f != null) await _upload(f.bytes, f.name, detect: true);
  }

  Future<void> _upload(List<int> bytes, String name, {bool detect = false}) async {
    setState(() => _uploading = true);
    try {
      final doc = await s.api.uploadDocument(s.userId!, bytes, name, documentType: detect ? null : 'utility_bill');
      setState(() {
        s.lastDocument = doc;
        if (doc['extracted_fields'] != null) {
          s.extractedBills.add({
            'document_type': doc['document_type'],
            ...(doc['extracted_fields'] as Map<String, dynamic>),
          });
        }
      });
    } catch (e) {
      if (mounted) showError(context, s, e);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Widget _status(bool done) => done
      ? const Icon(Icons.check_circle, color: TColor.good, semanticLabel: 'done')
      : const Icon(Icons.radio_button_unchecked, semanticLabel: 'not yet');

  @override
  Widget build(BuildContext context) {
    final fields = s.lastDocument?['extracted_fields'] as Map<String, dynamic>?;
    final docLabel = fields == null
        ? null
        : '${s.t('bill_done')}: ${fields['provider'] ?? fields['merchant_or_platform'] ?? fields['shop_name'] ?? ''}'
              ' · ৳${fields['amount_bdt'] ?? fields['page_total_bdt'] ?? ''}';
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('connect_title'),
        body: ListView(
          padding: const EdgeInsets.all(TSpace.lg),
          children: [
            if (s.consents.contains('sms')) ...[
              Card(
                child: ListTile(
                  key: const Key('import_sms'),
                  leading: const Icon(Icons.sms_outlined),
                  title: Text(s.t('import_sms')),
                  subtitle: s.sms.isEmpty ? null : Text('${num2(s.sms.length, s.lang)} ${s.t('sms_loaded')}'),
                  trailing: _status(s.sms.isNotEmpty),
                  onTap: _importSampleSms,
                ),
              ),
              if (kIsWeb)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(TSpace.md),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(s.t('web_sms_note'), style: const TextStyle(color: TColor.lightTextMuted)),
                        const SizedBox(height: TSpace.sm),
                        TextField(
                          key: const Key('sms_paste'),
                          controller: _paste,
                          minLines: 3,
                          maxLines: 6,
                          decoration: InputDecoration(
                            hintText: s.t('paste_sms_hint'),
                            border: const OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: TSpace.sm),
                        Wrap(
                          spacing: TSpace.sm,
                          children: [
                            OutlinedButton(
                              key: const Key('use_pasted'),
                              onPressed: () => _usePasted(_paste.text),
                              child: Text(s.t('use_pasted')),
                            ),
                            OutlinedButton.icon(
                              key: const Key('sms_txt'),
                              onPressed: _pickSmsFile,
                              icon: const Icon(Icons.upload_file),
                              label: Text(s.t('upload_txt')),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
            ],
            if (s.consents.contains('ocr') || s.consents.contains('bills')) ...[
              Card(
                child: ListTile(
                  key: const Key('upload_bill'),
                  leading: const Icon(Icons.receipt_long_outlined),
                  title: Text(s.t('upload_bill')),
                  subtitle: docLabel == null ? null : Text(docLabel),
                  trailing: _uploading
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
                      : _status(fields != null),
                  onTap: _uploading ? null : _uploadSample,
                ),
              ),
              if (kIsWeb)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: TSpace.xs),
                  child: Wrap(
                    spacing: TSpace.sm,
                    runSpacing: TSpace.sm,
                    children: [
                      OutlinedButton.icon(
                        key: const Key('pick_photo'),
                        onPressed: _uploading ? null : () => _pickPhoto(camera: false),
                        icon: const Icon(Icons.photo_library_outlined),
                        label: Text(s.t('choose_photo')),
                      ),
                      OutlinedButton.icon(
                        key: const Key('camera_photo'),
                        onPressed: _uploading ? null : () => _pickPhoto(camera: true),
                        icon: const Icon(Icons.photo_camera_outlined),
                        label: Text(s.t('take_photo')),
                      ),
                      Text(
                        s.t('drop_hint'),
                        style: const TextStyle(color: TColor.lightTextMuted, fontSize: TType.bodySmall),
                      ),
                    ],
                  ),
                ),
            ],
          ],
        ),
        bottom: FilledButton(
          key: const Key('get_score'),
          onPressed: () {
            if (s.personaKey == 'real_user' &&
                (s.extractedTransactions.isNotEmpty || s.extractedBills.isNotEmpty)) {
              context.push(Routes.review);
            } else {
              context.push(Routes.processing);
            }
          },
          child: Text(
            s.personaKey == 'real_user' &&
                    (s.extractedTransactions.isNotEmpty || s.extractedBills.isNotEmpty)
                ? s.t('review_title')
                : s.t('get_score'),
          ),
        ),
      ),
    );
  }
}
