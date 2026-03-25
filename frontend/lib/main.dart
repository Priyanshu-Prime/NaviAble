/// NaviAble Flutter Web Application — Entry Point
///
/// This is the main entry point for the NaviAble Flutter web application.
/// It initialises the Riverpod [ProviderScope] at the root of the widget tree,
/// which makes all state providers available to every descendant widget without
/// requiring manual dependency injection.
///
/// Architecture:
/// ```
/// ProviderScope (Riverpod root)
///   └── NaviAbleApp (MaterialApp)
///         └── HomeScreen (main form + results)
/// ```
library main;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

void main() {
  // ensureInitialized is required by flutter_image_compress on some platforms.
  WidgetsFlutterBinding.ensureInitialized();

  runApp(
    // ProviderScope is the Riverpod container.  All providers declared in
    // lib/providers/ are lazily initialised inside this scope.
    const ProviderScope(
      child: NaviAbleApp(),
    ),
  );
}

/// Root [MaterialApp] for the NaviAble platform.
///
/// Uses [NaviAbleTheme.light] to ensure WCAG AA compliant contrast ratios
/// throughout the UI, satisfying the accessibility mandate in
/// `.agent/system/CONSTRAINTS_AND_RULES.md`.
class NaviAbleApp extends StatelessWidget {
  const NaviAbleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NaviAble — Accessibility Verification',
      debugShowCheckedModeBanner: false,
      theme: NaviAbleTheme.light,
      home: const HomeScreen(),
    );
  }
}
