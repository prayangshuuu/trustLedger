import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'processing_screen.dart';
import 'scaffold.dart';

class ConnectDataScreen extends StatefulWidget {
  const ConnectDataScreen({super.key, required this.state});

  final AppState state;

  @override
  State<ConnectDataScreen> createState() => _ConnectDataScreenState();
}

class _ConnectDataScreenState extends State<ConnectDataScreen> {
  bool _uploading = false;

  Future<void> _importSms() async {
    // Demo: sample SMS bundled with the app. On a real phone the SMS are read on-device.
    final raw = await rootBundle.loadString('assets/demo/shathi_sms.json');
    final data = jsonDecode(raw) as Map<String, dynamic>;
    setState(() => widget.state.sms = (data['sms'] as List).cast<String>());
  }

  Future<void> _uploadBill() async {
    final s = widget.state;
    setState(() => _uploading = true);
    try {
      final bytes = await rootBundle.load('assets/demo/desco_bill.jpg');
      final doc = await s.api.uploadDocument(s.userId!, bytes.buffer.asUint8List(), 'desco_bill.jpg');
      setState(() => s.lastDocument = doc);
    } catch (e) {
      if (mounted) showError(context, s, e, onRetry: _uploadBill);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    final fields = s.lastDocument?['extracted_fields'] as Map<String, dynamic>?;
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('connect_title'),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (s.consents.contains('sms'))
              Card(
                child: ListTile(
                  key: const Key('import_sms'),
                  leading: const Icon(Icons.sms_outlined),
                  title: Text(s.t('import_sms')),
                  subtitle: s.sms.isEmpty ? null : Text('${num2(s.sms.length, s.lang)} ${s.t('sms_loaded')}'),
                  trailing: s.sms.isEmpty
                      ? const Icon(Icons.download)
                      : const Icon(Icons.check_circle, color: Colors.green),
                  onTap: _importSms,
                ),
              ),
            if (s.consents.contains('ocr') || s.consents.contains('bills'))
              Card(
                child: ListTile(
                  key: const Key('upload_bill'),
                  leading: const Icon(Icons.receipt_long_outlined),
                  title: Text(s.t('upload_bill')),
                  subtitle: fields == null
                      ? null
                      : Text('${s.t('bill_done')}: ${fields['provider'] ?? ''} · ৳${fields['amount_bdt'] ?? ''}'),
                  trailing: _uploading
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
                      : (fields == null
                            ? const Icon(Icons.upload)
                            : const Icon(Icons.check_circle, color: Colors.green)),
                  onTap: _uploading ? null : _uploadBill,
                ),
              ),
          ],
        ),
        bottom: FilledButton(
          key: const Key('get_score'),
          onPressed: () =>
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ProcessingScreen(state: s))),
          child: Text(s.t('get_score')),
        ),
      ),
    );
  }
}
