import React from "react";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import Skeleton from "antd/lib/skeleton";
import Switch from "antd/lib/switch";
import Alert from "antd/lib/alert";
import DynamicComponent from "@/components/DynamicComponent";
import { SettingsEditorPropTypes, SettingsEditorDefaultProps } from "../prop-types";

export default function CASSettings(props) {
  const { values, onChange, loading } = props;

  return (
    <DynamicComponent name="OrganizationSettings.CASSettings" {...props}>
      <h4>CAS Authentication</h4>
      <Form.Item label="Enable CAS Authentication">
        {loading ? (
          <Skeleton title={{ width: 300 }} paragraph={false} active />
        ) : (
          <Switch
            checked={values.auth_cas_enabled}
            onChange={enabled => onChange({ auth_cas_enabled: enabled })}
          />
        )}
      </Form.Item>

      {values.auth_cas_enabled && (
        <>
          <Form.Item label="CAS Server URL" required>
            <Input
              placeholder="https://cas.example.com/cas/"
              value={values.auth_cas_server_url}
              onChange={e => onChange({ auth_cas_server_url: e.target.value })}
            />
          </Form.Item>

          <Form.Item label="Protocol Version">
            <Input
              type="number"
              min="2"
              max="3"
              value={values.auth_cas_protocol_version || 2}
              onChange={e => onChange({ auth_cas_protocol_version: parseInt(e.target.value, 10) })}
            />
            <p className="text-muted">Typically 2 or 3</p>
          </Form.Item>

          <Alert
            message={
              <p>
                When enabled, users will be able to login using CAS credentials.
                New users will be automatically created and added to the <strong>Default</strong> group.
              </p>
            }
            type="info"
            className="m-t-15"
          />
        </>
      )}
    </DynamicComponent>
  );
}

CASSettings.propTypes = SettingsEditorPropTypes;
CASSettings.defaultProps = SettingsEditorDefaultProps;
