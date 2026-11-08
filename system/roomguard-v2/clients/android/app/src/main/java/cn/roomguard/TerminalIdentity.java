package cn.roomguard;
import android.content.Context;import android.content.SharedPreferences;import java.util.UUID;
public final class TerminalIdentity {public static synchronized String get(Context context){SharedPreferences p=context.getSharedPreferences("rg",0);String id=p.getString("terminal_id","");if(id.isEmpty()){id="apk-"+UUID.randomUUID().toString();p.edit().putString("terminal_id",id).apply();}return id;}}
