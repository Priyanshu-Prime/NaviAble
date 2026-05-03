import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'screens/map_screen.dart';
import 'screens/place_detail_screen.dart';
import 'screens/contribute_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: NaviAbleApp()));
}

final _router = GoRouter(
  initialLocation: '/map',
  routes: [
    GoRoute(
      path: '/map',
      builder: (_, __) => const MapScreen(),
    ),
    GoRoute(
      path: '/place/:gid',
      builder: (_, st) => PlaceDetailScreen(
        googlePlaceId: st.pathParameters['gid']!,
      ),
    ),
    GoRoute(
      path: '/contribute',
      builder: (_, st) {
        final extra = st.extra as Map<String, dynamic>?;
        return ContributeScreen(
          presetGooglePlaceId: extra?['gid'] as String?,
          presetPlaceName: extra?['name'] as String?,
        );
      },
    ),
  ],
);

class NaviAbleApp extends StatelessWidget {
  const NaviAbleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'NaviAble',
      debugShowCheckedModeBanner: false,
      theme: NaviAbleTheme.light,
      darkTheme: NaviAbleTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: _router,
    );
  }
}
