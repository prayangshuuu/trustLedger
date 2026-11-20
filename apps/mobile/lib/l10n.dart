/// UI strings. Bangla is the default language; English is the toggle.
const Map<String, Map<String, String>> _strings = {
  'app_name': {'bn': 'ট্রাস্টলেজার', 'en': 'TrustLedger'},
  'tagline': {
    'bn': 'আপনার ফোনের অভ্যাসই আপনার ক্রেডিট পরিচয়। ন্যায্য, গোপনীয় ও ব্যাখ্যাযোগ্য।',
    'en': 'Your phone habits become your credit identity. Fair, private and explainable.',
  },
  'start': {'bn': 'শুরু করুন', 'en': 'Get started'},
  'demo_mode': {'bn': 'ডেমো মোড: একটি চরিত্র বেছে নিন', 'en': 'Demo mode: pick a persona'},
  'consent_title': {'bn': 'আপনার সম্মতি', 'en': 'Your consent'},
  'consent_intro': {
    'bn': 'কোন তথ্য ব্যবহার করা যাবে আপনি ঠিক করুন। যেকোনো সময় সেটিংস থেকে বন্ধ করতে পারবেন।',
    'en': 'You decide which data we may use. You can turn any of it off later in Settings.',
  },
  'src_sms': {'bn': 'লেনদেনের এসএমএস', 'en': 'Transaction SMS'},
  'src_sms_d': {
    'bn': 'মোবাইল ওয়ালেটের এসএমএস থেকে শুধু হিসাব (আয়, বিল, সঞ্চয়)। কাঁচা এসএমএস সংরক্ষণ হয় না।',
    'en': 'Only totals from wallet SMS (income, bills, savings). Raw SMS is never stored.',
  },
  'src_bills': {'bn': 'ইউটিলিটি বিল', 'en': 'Utility bills'},
  'src_bills_d': {'bn': 'বিল সময়মতো দিচ্ছেন কিনা দেখতে।', 'en': 'To see if bills are paid on time.'},
  'src_recharge': {'bn': 'মোবাইল রিচার্জ', 'en': 'Mobile recharge'},
  'src_recharge_d': {'bn': 'রিচার্জের নিয়মিততা।', 'en': 'How regularly you recharge.'},
  'src_ocr': {'bn': 'বিলের ছবি (ওসিআর)', 'en': 'Bill photos (OCR)'},
  'src_ocr_d': {
    'bn': 'ছবি এনক্রিপ্ট করে সর্বোচ্চ ৩০ দিন রাখা হয়।',
    'en': 'Photos are encrypted and kept for at most 30 days.',
  },
  'src_bhorsha': {'bn': 'ভরসা কথোপকথন', 'en': 'Bhorsha chat'},
  'src_bhorsha_d': {
    'bn': 'ইতিহাস না থাকলে ১০-১২টি সহজ প্রশ্ন।',
    'en': '10-12 simple questions if you have no history.',
  },
  'continue': {'bn': 'এগিয়ে যান', 'en': 'Continue'},
  'connect_title': {'bn': 'তথ্য যুক্ত করুন', 'en': 'Connect your data'},
  'import_sms': {'bn': 'নমুনা এসএমএস আনুন', 'en': 'Import sample SMS'},
  'sms_loaded': {'bn': 'টি এসএমএস প্রস্তুত (ফোনেই থাকে, ডেমোতে পাঠানো হয়)', 'en': 'SMS ready (demo only)'},
  'upload_bill': {'bn': 'বিলের ছবি আপলোড করুন', 'en': 'Upload a bill photo'},
  'bill_done': {'bn': 'বিল পড়া হয়েছে', 'en': 'Bill read'},
  'get_score': {'bn': 'আমার স্কোর দেখুন', 'en': 'See my score'},
  'processing': {'bn': 'আপনার তথ্য যাচাই হচ্ছে…', 'en': 'Checking your data…'},
  'step_data_agent': {'bn': 'তথ্য প্রস্তুত', 'en': 'Data prepared'},
  'step_bhorsha_router': {'bn': 'ইতিহাস যাচাই', 'en': 'History checked'},
  'step_scoring_agent': {'bn': 'স্কোর হিসাব', 'en': 'Score computed'},
  'step_explainer_agent': {'bn': 'কারণ ব্যাখ্যা', 'en': 'Reasons explained'},
  'step_fairness_agent': {'bn': 'ন্যায্যতা যাচাই', 'en': 'Fairness checked'},
  'step_finalize': {'bn': 'সিদ্ধান্ত সংরক্ষিত', 'en': 'Decision saved'},
  'your_score': {'bn': 'আপনার ট্রাস্টলেজার স্কোর', 'en': 'Your TrustLedger score'},
  'band_Excellent': {'bn': 'চমৎকার', 'en': 'Excellent'},
  'band_Good': {'bn': 'ভালো', 'en': 'Good'},
  'band_Fair': {'bn': 'মোটামুটি', 'en': 'Fair'},
  'band_Building': {'bn': 'গড়ে উঠছে', 'en': 'Building'},
  'why': {'bn': 'কেন এই স্কোর?', 'en': 'Why this score?'},
  'helped': {'bn': 'যা সাহায্য করেছে', 'en': 'What helped'},
  'improve': {'bn': 'যা উন্নত করা যায়', 'en': 'What to improve'},
  'tips': {'bn': 'পরামর্শ', 'en': 'Tips'},
  'source': {'bn': 'সূত্র', 'en': 'Source'},
  'see_offer': {'bn': 'ঋণ প্রস্তাব দেখুন', 'en': 'See loan offer'},
  'offer_title': {'bn': 'আপনার ঋণ প্রস্তাব', 'en': 'Your loan offer'},
  'offer_amount': {'bn': 'ঋণের পরিমাণ', 'en': 'Loan amount'},
  'installments': {'bn': '৩ মাসিক কিস্তি', 'en': '3 monthly installments'},
  'accept': {'bn': 'গ্রহণ করুন', 'en': 'Accept'},
  'review': {
    'bn': 'আপনার আবেদনটি একজন কর্মকর্তা দেখবেন। ফল শীঘ্রই জানানো হবে।',
    'en': 'A loan officer will review your application soon.',
  },
  'rejected': {
    'bn': 'এবার অনুমোদন হয়নি। নিচের পরামর্শগুলো মানলে স্কোর বাড়বে।',
    'en': 'Not approved this time. Following the tips below will raise your score.',
  },
  'repay_title': {'bn': 'কিস্তি ও ঋণসীমা', 'en': 'Repayments and limit'},
  'pay_installment': {'bn': 'কিস্তি পরিশোধ করুন', 'en': 'Pay installment'},
  'paid_on_time': {'bn': 'সময়মতো পরিশোধ', 'en': 'Paid on time'},
  'limit_ladder': {'bn': 'ঋণসীমার সিঁড়ি', 'en': 'Limit ladder'},
  'ladder_hint': {
    'bn': 'পরপর ৩টি কিস্তি সময়মতো দিলে ঋণসীমা ২০% বাড়ে।',
    'en': '3 on-time installments raise your limit by 20%.',
  },
  'unlock_limit': {'bn': 'নতুন ঋণসীমা চালু করুন', 'en': 'Unlock new limit'},
  'current_limit': {'bn': 'বর্তমান ঋণসীমা', 'en': 'Current limit'},
  'bhorsha_title': {'bn': 'ভরসা কথোপকথন', 'en': 'Bhorsha chat'},
  'bhorsha_intro': {
    'bn': 'আপনার কোনো ওয়ালেট ইতিহাস নেই, তাই কিছু সহজ প্রশ্ন করব। নিজের অভিজ্ঞতা থেকে উত্তর দিন।',
    'en': 'You have no wallet history, so I will ask a few simple questions. Answer from your own life.',
  },
  'type_answer': {'bn': 'আপনার উত্তর লিখুন…', 'en': 'Type your answer…'},
  'send': {'bn': 'পাঠান', 'en': 'Send'},
  'bhorsha_done': {'bn': 'মূল্যায়ন শেষ! স্কোর দেখুন', 'en': 'Done! See your score'},
  'settings': {'bn': 'সেটিংস', 'en': 'Settings'},
  'active_consents': {'bn': 'চালু সম্মতি', 'en': 'Active consents'},
  'revoke': {'bn': 'বন্ধ করুন', 'en': 'Revoke'},
  'delete_data': {'bn': 'আমার সব তথ্য মুছুন', 'en': 'Delete all my data'},
  'delete_confirm': {
    'bn': 'আপনার সব তথ্য স্থায়ীভাবে মুছে যাবে। নিশ্চিত?',
    'en': 'All your data will be permanently deleted. Are you sure?',
  },
  'deleted': {'bn': 'আপনার সব তথ্য মুছে ফেলা হয়েছে।', 'en': 'All your data has been deleted.'},
  'cancel': {'bn': 'বাতিল', 'en': 'Cancel'},
  'confirm': {'bn': 'হ্যাঁ, মুছুন', 'en': 'Yes, delete'},
  'retry': {'bn': 'আবার চেষ্টা করুন', 'en': 'Try again'},
  'err_network': {
    'bn': 'ইন্টারনেট সংযোগ পাওয়া যাচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।',
    'en': 'No internet connection. Check your connection and try again.',
  },
  'err_server': {
    'bn': 'সার্ভারে সমস্যা হয়েছে। কিছুক্ষণ পর আবার চেষ্টা করুন।',
    'en': 'Server problem. Please try again shortly.',
  },
  'err_consent': {'bn': 'এই কাজের জন্য আপনার সম্মতি প্রয়োজন।', 'en': 'Your consent is needed for this.'},
  'err_generic': {'bn': 'কিছু একটা ভুল হয়েছে।', 'en': 'Something went wrong.'},
  'home': {'bn': 'প্রথম পাতা', 'en': 'Home'},
};

String tr(String key, String lang) => _strings[key]?[lang] ?? _strings[key]?['en'] ?? key;

const _bnDigits = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];

/// Format a number with Bangla digits when the language is Bangla.
String num2(num value, String lang) {
  final s = value is int ? value.toString() : value.toStringAsFixed(0);
  if (lang != 'bn') return s;
  return s.split('').map((c) => int.tryParse(c) != null ? _bnDigits[int.parse(c)] : c).join();
}
