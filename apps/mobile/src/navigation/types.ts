import { NavigatorScreenParams } from '@react-navigation/native';
import { DocumentScanType } from '../services/scanner';

export type BottomTabParamList = {
  Home: undefined;
  BillNyay: { caseId?: string; scanCompleted?: boolean } | undefined;
  DaaviSetu: { caseId?: string; scanCompleted?: boolean } | undefined;
  BimaNyay: { caseId?: string; scanCompleted?: boolean } | undefined;
  SchemeSetu: undefined;
  DawaCheck: { caseId?: string; scanCompleted?: boolean } | undefined;
};

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<BottomTabParamList>;
  CameraScan: {
    documentType?: DocumentScanType;
    onScanComplete?: (doc: any) => void;
    /** Tab to return to after upload; overrides the documentType default. */
    returnTo?: 'BillNyay' | 'DaaviSetu' | 'BimaNyay' | 'DawaCheck';
  };
};
