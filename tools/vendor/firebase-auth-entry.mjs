// Built with pinned Firebase 12.4.0. Browser persistence is deliberately disabled.
import {initializeApp,getApps} from 'firebase/app';
import {getAuth,GoogleAuthProvider,inMemoryPersistence,setPersistence,signInWithPopup,signOut} from 'firebase/auth';
export async function googlePopup(config){
 const app=getApps().find(a=>a.name==='LingoLive')||initializeApp(config,'LingoLive');
 const auth=getAuth(app);await setPersistence(auth,inMemoryPersistence);
 const provider=new GoogleAuthProvider();provider.setCustomParameters({prompt:'select_account'});
 try{const result=await signInWithPopup(auth,provider);return await result.user.getIdToken();}
 finally{await signOut(auth);}
}
export async function prepare(config){
 const app=getApps().find(a=>a.name==='LingoLive')||initializeApp(config,'LingoLive');
 await setPersistence(getAuth(app),inMemoryPersistence);
}
