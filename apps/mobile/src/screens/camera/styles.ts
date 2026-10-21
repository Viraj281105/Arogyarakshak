import { Platform, StyleSheet } from 'react-native';

const corner = { position: 'absolute' as const, width: 24, height: 24 };

/** Layout for the document scanner (colours come from the theme at render time). */
export const cameraStyles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'space-between',
  },
  permissionCard: {
    borderWidth: 1,
  },
  permissionTitle: {
    letterSpacing: -0.3,
  },
  permissionMsg: {
    lineHeight: 22,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Platform.OS === 'android' ? 16 : 8,
    zIndex: 10,
  },
  iconButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    color: '#ffffff',
    fontSize: 20,
  },
  typeSelector: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 12,
    zIndex: 10,
  },
  typeTab: {
    flex: 1,
    marginHorizontal: 3,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  typeTabText: {
    fontSize: 12,
    textAlign: 'center',
  },
  viewfinderContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  viewfinderFrame: {
    width: '100%',
    aspectRatio: 3 / 4,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderRadius: 12,
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cornerTL: { ...corner, top: -2, left: -2, borderTopWidth: 4, borderLeftWidth: 4 },
  cornerTR: { ...corner, top: -2, right: -2, borderTopWidth: 4, borderRightWidth: 4 },
  cornerBL: { ...corner, bottom: -2, left: -2, borderBottomWidth: 4, borderLeftWidth: 4 },
  cornerBR: { ...corner, bottom: -2, right: -2, borderBottomWidth: 4, borderRightWidth: 4 },
  frameInstruction: {
    color: '#ffffff',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    overflow: 'hidden',
  },
  statusOverlay: {
    position: 'absolute',
    top: '35%',
    left: 24,
    right: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(6, 182, 212, 0.4)',
    zIndex: 50,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottomControls: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  byodNotice: {
    color: '#94a3b8',
    marginBottom: 16,
    textAlign: 'center',
  },
  consentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
    paddingHorizontal: 16,
  },
  consentBox: {
    width: 18,
    height: 18,
    borderWidth: 2,
    borderRadius: 4,
    marginRight: 10,
  },
  consentLabel: {
    color: '#cbd5e1',
    flexShrink: 1,
  },
  shutterButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
  },
});
