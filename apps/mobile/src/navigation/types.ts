import { NavigatorScreenParams } from '@react-navigation/native';
import { DocumentScanType } from '../services/scanner';

export type BottomTabParamList = {
  Home: undefined;
  BillNyay: undefined;
  DaaviSetu: undefined;
  BimaNyay: undefined;
  SchemeSetu: undefined;
  DawaCheck: undefined;
};

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<BottomTabParamList>;
  CameraScan: {
    documentType?: DocumentScanType;
    onScanComplete?: (doc: any) => void;
  };
};
